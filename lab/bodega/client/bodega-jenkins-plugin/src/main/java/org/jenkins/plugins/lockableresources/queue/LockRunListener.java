/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2013, 6WIND S.A. All rights reserved.                 *
 *                                                                     *
 * This file is part of the Jenkins Lockable Resources Plugin and is   *
 * published under the MIT license.                                    *
 *                                                                     *
 * See the "LICENSE.txt" file for more information.                    *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
package org.jenkins.plugins.lockableresources.queue;

import com.google.gson.Gson;
import com.rubrik.bodega.client.BodegaService;
import com.rubrik.bodega.client.BodegaServiceUtil;
import com.rubrik.bodega.client.Order;
import com.rubrik.bodega.client.OrderUpdate;

import com.rubrik.bodega.client.RktestYml;
import com.rubrik.bodega.client.SdDevMachine;
import com.timgroup.statsd.StatsDClient;
import hudson.Extension;
import hudson.matrix.MatrixBuild;
import hudson.model.AbstractBuild;
import hudson.model.AbstractProject;
import hudson.model.Queue;
import hudson.model.listeners.RunListener;
import hudson.model.Node;
import hudson.model.ParametersAction;
import hudson.model.ParameterValue;
import hudson.model.StringParameterValue;
import hudson.model.TaskListener;

import java.lang.StringBuilder;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import jenkins.model.Jenkins;

import org.jenkins.plugins.lockableresources.LockableResourcesManager;
import org.jenkins.plugins.lockableresources.LockableResource;
import org.jenkins.plugins.lockableresources.actions.LockedResourcesBuildAction;
import org.jenkins.plugins.lockableresources.actions.BodegaOrderAction;

@Extension
public class LockRunListener extends RunListener<AbstractBuild<?, ?>> {
    static final String LOG_PREFIX = "[lockable-resources]";
    static final Logger LOGGER =
        Logger.getLogger(LockRunListener.class.getName());

    @Override
    public void onStarted(AbstractBuild<?, ?> build, TaskListener listener) {
        // Skip locking for multiple configuration projects,
        // only the child jobs will actually lock resources.
        if (build instanceof MatrixBuild)
            return;

        BodegaOrderAction bodegaOrderAction =
            build.getAction(BodegaOrderAction.class);
        if (bodegaOrderAction != null) {
            BodegaService bodega =
                LockableResourcesManager.get().getBodegaService();
            try {
                Order order = BodegaServiceUtil.getResponse(
                    bodega.getOrder(bodegaOrderAction.orderSid));
                String buildUrl = getBuildUrl(build);
                if (order.status != Order.Status.FULFILLED) {
                    String message =
                        "Order " + order.sid + " is expected to be " +
                        Order.Status.FULFILLED + " but instead is " +
                        order.status + ". The order may have gone over " +
                        "its limit or something else happened to it. " +
                        "Aborting build " + buildUrl;
                    PrintStream buildConsole = listener.getLogger();
                    buildConsole.println(message);
                    build.doStop();
                    return;
                }

                OrderUpdate update = new OrderUpdate();
                update.orderSid = bodegaOrderAction.orderSid;
                update.timeLimitDelta = "24:00:00";
                update.comment =
                    "For just-started Jenkins build " + buildUrl;
                LOGGER.log(
                    Level.FINE,
                    "Adding update to Bodega order " +
                    bodegaOrderAction.orderSid +
                    " indicating it's for build " +
                    build.getFullDisplayName());
                publishPrepTimeStats(build,bodegaOrderAction);
                OrderUpdate confirmedUpdate = BodegaServiceUtil.getResponse(
                    bodega.createOrderUpdate(update));
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to start build " + build.getFullDisplayName() +
                    " using Bodega order " + bodegaOrderAction.orderSid,
                    e);
            }
            return;
        }

        AbstractProject<?, ?> proj = Utils.getProject(build);
        List<LockableResource> required = new ArrayList<LockableResource>();
        if (proj != null) {
            LockableResourcesStruct resources = Utils.requiredResources(proj);
            if (resources != null) {
                if (resources.requiredNumber != null ||
                    !resources.label.isEmpty()) {
                    required = LockableResourcesManager.get()
                        .getResourcesFromProject(proj.getFullName());
                } else {
                    required = resources.required;
                }

                if (LockableResourcesManager.get().lock(required, build)) {
                    build.addAction(LockedResourcesBuildAction
                        .fromResources(required));
                    listener.getLogger().printf("%s acquired lock on %s\n",
                        LOG_PREFIX, required);
                    LOGGER.fine(build.getFullDisplayName()
                        + " acquired lock on " + required);
                    if (resources.requiredVar != null) {
                        List<ParameterValue> params =
                            new ArrayList<ParameterValue>();
                        // Populate Job environment variable string sans spaces
                        String envVarString = required.toString();
                        envVarString = envVarString.replaceAll("[\\]\\[]", "");
                        envVarString = envVarString.replaceAll("( )+", "");
                        params.add(new StringParameterValue(
                            resources.requiredVar, envVarString));
                        build.addAction(new ParametersAction(params));
                    }
                    // Inject environment variable with the label used.
                    if (!resources.label.isEmpty()) {
                        List<ParameterValue> params =
                            new ArrayList<ParameterValue>();
                        params.add(new StringParameterValue(
                                    "LOCKABLE_RESOURCE_LABEL",
                                    resources.label));
                        build.addAction(new ParametersAction(params));
                    }
                } else {
                    listener.getLogger().printf("%s failed to lock %s\n",
                        LOG_PREFIX, required);
                    LOGGER.fine(build.getFullDisplayName() + " failed to lock "
                        + required);
                }
            }
        }
    }

    @Override
    public void onCompleted(AbstractBuild<?, ?> build, TaskListener listener) {
        // Skip unlocking for multiple configuration projects,
        // only the child jobs will actually unlock resources.
        if (build instanceof MatrixBuild)
            return;

        BodegaOrderAction bodegaOrderAction =
            build.getAction(BodegaOrderAction.class);
        if (bodegaOrderAction != null) {
            BodegaService bodega =
                LockableResourcesManager.get().getBodegaService();
            try {
                closeOrderForBuild(bodega, build, bodegaOrderAction);
                return;
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to close Bodega order " +
                    bodegaOrderAction.orderSid +
                    " for completed build " +
                    build.getFullDisplayName(),
                    e);
            }
        }

        // obviously project name cannot be obtained here
        List<LockableResource> required = LockableResourcesManager.get()
            .getResourcesFromBuild(build);
        if (required.size() > 0) {
            LockableResourcesManager.get().reserve(required,
                                                   "Bugfiler Bot",
                                                   "Force");
            listener.getLogger().printf("%s Reserved %s by Bugfiler Bot\n",
                                        LOG_PREFIX, required);
            LOGGER.fine(build.getFullDisplayName() + " reserved for clean-up"
                + required);
        }
    }

    @Override
    public void onDeleted(AbstractBuild<?, ?> build) {
        // Skip unlocking for multiple configuration projects,
        // only the child jobs will actually unlock resources.
        if (build instanceof MatrixBuild)
            return;

        BodegaOrderAction bodegaOrderAction =
            build.getAction(BodegaOrderAction.class);
        if (bodegaOrderAction != null) {
            BodegaService bodega =
                LockableResourcesManager.get().getBodegaService();
            try {
                closeOrderForBuild(bodega, build, bodegaOrderAction);
                return;
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to close Bodega order " +
                    bodegaOrderAction.orderSid +
                    " for deleted build " +
                    build.getFullDisplayName(),
                    e);
            }
        }

        List<LockableResource> required = LockableResourcesManager.get()
            .getResourcesFromBuild(build);
        if (required.size() > 0) {
            LockableResourcesManager.get().reserve(required,
                                                   "Bugfiler Bot",
                                                   "Force");
            LOGGER.fine(build.getFullDisplayName() + " reserved for clean-up"
                + required);
        }
    }

    private String getBuildUrl(AbstractBuild<?, ?> build) {
        return Jenkins.getInstance().getRootUrl() + build.getUrl();
    }

    private String getBuildString(AbstractBuild<?, ?> build) {
        return getBuildUrl(build) + " (" + build.getResult().toString() + ")";
    }

    private void closeOrderForBuild(
        BodegaService bodega,
        AbstractBuild<?, ?> build,
        BodegaOrderAction bodegaOrderAction) throws Exception {

        if (bodegaOrderAction.jenkinsNodeName != null) {
            Jenkins jenkins = Jenkins.getInstance();
            Node node = jenkins.getNode(bodegaOrderAction.jenkinsNodeName);
            jenkins.removeNode(node);
        }
        publishDynapodSpecificStats(build, bodegaOrderAction);
        OrderUpdate update = new OrderUpdate();
        update.orderSid = bodegaOrderAction.orderSid;
        update.newStatus = Order.Status.CLOSED;
        update.comment = "Was for Jenkins build " + getBuildString(build);
        OrderUpdate confirmedUpdate = BodegaServiceUtil.getResponse(
            bodega.createOrderUpdate(update));
    }

    private void publishDynapodSpecificStats(
      AbstractBuild<?, ?> build,
      BodegaOrderAction bodegaOrderAction) {
        try {
          final Order order = bodegaOrderAction.getOrder();
          final RktestYml pod = order.getFulfilledItem("pod", RktestYml.class);
          String dynapodFileName = pod.filename.replace(".", "_");
          LOGGER.log(
            Level.FINER,
            "Logging build result for given pod {0}",
            dynapodFileName);
          final String statName = String.format(
            "%s.%s.%s",
            dynapodFileName,
            build.getProject().getName(),
            build.getResult());
          final StatsDClient statsdClient =
            LockableResourcesManager.get().getOrCreateStatsdClient();
          statsdClient.increment(statName);
        } catch (Exception e) {
            LOGGER.log(Level.WARNING,
              "Could not publish dynapod specific stats", e);
        }
    }

    private void publishPrepTimeStats(
      AbstractBuild<?, ?> build,
      BodegaOrderAction bodegaOrderAction) {
        try {
            final StatsDClient statsDClient =
              LockableResourcesManager.get().getOrCreateStatsdClient();
            final String taskPreparationStat =
              String.format("%s.prepared",build.getProject().getName());
            LOGGER.log(
              Level.FINE,"Incrementing {0} metric", taskPreparationStat);
            statsDClient.increment(taskPreparationStat);
            long perceivedDuration = System.currentTimeMillis() -
              bodegaOrderAction.getOrderRequestTime();
            LOGGER.log(
              Level.FINE,
              "Recording time taken {0} ms for order fulfilment",
              perceivedDuration);
            statsDClient.recordExecutionTime(
              taskPreparationStat,
              perceivedDuration);
        } catch (Exception e) {
            LOGGER.log(Level.WARNING,"Could not publish order stats", e);
        }
    }
}
