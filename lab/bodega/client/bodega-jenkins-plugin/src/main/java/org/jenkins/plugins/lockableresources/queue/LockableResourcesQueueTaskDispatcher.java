/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2013, 6WIND S.A. All rights reserved.                 *
 *                                                                     *
 * This file is part of the Jenkins Lockable Resources Plugin and is   *
 * published under the MIT license.                                    *
 *                                                                     *
 * See the "LICENSE.txt" file for more information.                    *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
package org.jenkins.plugins.lockableresources.queue;

import com.cloudbees.plugins.credentials.Credentials;
import com.cloudbees.plugins.credentials.CredentialsMatchers;
import com.cloudbees.plugins.credentials.CredentialsProvider;
import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.reflect.TypeToken;
import com.rubrik.bodega.client.BodegaService;
import com.rubrik.bodega.client.BodegaServiceUtil;
import com.rubrik.bodega.client.Order;
import com.rubrik.bodega.client.OrderItem;
import com.rubrik.bodega.client.ReleaseQualBaton;
import com.rubrik.bodega.client.RktestYml;
import com.rubrik.bodega.client.CockroachDBDepsMachine;
import com.rubrik.bodega.client.SdDevMachine;
import com.rubrik.tivan.client.Artifact;
import com.timgroup.statsd.StatsDClient;
import com.uber.jenkins.phabricator.conduit.ConduitAPIClient;
import com.uber.jenkins.phabricator.credentials.ConduitCredentials;
import com.uber.jenkins.phabricator.PhabricatorBuildWrapperDescriptor;

import hudson.Extension;
import hudson.matrix.MatrixConfiguration;
import hudson.matrix.MatrixProject;
import hudson.model.AbstractProject;
import hudson.model.Node;
import hudson.model.Queue;
import hudson.model.Run;
import hudson.model.queue.QueueTaskDispatcher;
import hudson.model.queue.CauseOfBlockage;
import hudson.model.ParametersAction;
import hudson.model.ParameterValue;
import hudson.model.StringParameterValue;
import hudson.plugins.git.BranchSpec;
import hudson.plugins.git.GitSCM;
import hudson.plugins.git.UserRemoteConfig;
import hudson.plugins.sshslaves.SSHConnector;
import hudson.scm.NullSCM;
import hudson.scm.SCM;
import hudson.slaves.ComputerConnector;
import hudson.slaves.ComputerLauncher;
import hudson.slaves.DumbSlave;
import hudson.slaves.NodeProperty;
import hudson.slaves.RetentionStrategy;

import java.lang.StringBuilder;
import java.lang.UnsupportedOperationException;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URL;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.Random;
import java.util.logging.Level;
import java.util.logging.Logger;

import jenkins.model.Jenkins;

import net.sf.json.JSONObject;

import org.kohsuke.github.GHContent;
import org.kohsuke.github.GHRepository;
import org.kohsuke.github.GitHub;
import org.jenkins.plugins.lockableresources.LockableResource;
import org.jenkins.plugins.lockableresources.LockableResourcesManager;
import org.jenkins.plugins.lockableresources.actions.BodegaOrderAction;
import org.jenkinsci.plugins.envinject.EnvInjectNodeProperty;
import org.jenkinsci.plugins.plaincredentials.StringCredentials;
import org.jvnet.jenkins.plugins.nodelabelparameter.LabelParameterValue;


@Extension(ordinal = -1)
public class LockableResourcesQueueTaskDispatcher extends QueueTaskDispatcher {
    static final Logger LOGGER = Logger.getLogger(
        LockableResourcesQueueTaskDispatcher.class.getName());

    // This is the global default sd_dev_botstrap hash version that we will
    // fall back to if we can't determine an appropriate version for a given
    // build. It should hopefully never be needed but otherwise should be a
    // "safe" choice that works for as many cases as possible.
    static private final String defaultSdDevBootstrapHash =
        "8a72da80bb385f436c12b2d0e0488f177b5fde34";

    @Override
    public CauseOfBlockage canRun(Queue.Item item) {
        // Skip locking for multiple configuration projects,
        // only the child jobs will actually lock resources.
        if (item.task instanceof MatrixProject)
            return null;

        AbstractProject<?, ?> project = Utils.getProject(item);
        if (project == null)
            return null;

        LockableResourcesStruct resources = Utils.requiredResources(project);
        if (resources == null) {
            LOGGER.finest("Project " + project.getName() + " does not " +
              "require any resources to run.");

            String slaveLabelToUse = Utils.getDefaultSlaveLabel(project);
            if (slaveLabelToUse != null) {

              LOGGER.finer("Item has a default label of " + slaveLabelToUse +
                " so explicitly inject SLAVE_LABEL parameter to the build.");

              LabelParameterValue slaveLabelParam =
                new LabelParameterValue("SLAVE_LABEL", slaveLabelToUse);
              slaveLabelParam.setLabel(slaveLabelToUse);
              setParameterValue(item, slaveLabelParam);
            }

            return null;
        }

        /* *
         * This is Rubrik's point of interjection for handling the exception
         * use cases while making the resource selection.
         * Our current exception use cases are
         * 1. Override the lockable resource label to use. For example, if a
         *    particular test is configured to run on resources with label X,
         *    however we want to change that at run time to use label Y, we
         *    look for parameter called LOCKABLE_RESOURCE_LABEL in any of the
         *    attached actions of type ParametersAction.class.
         * 2. Enforce that resource selected is co-located with slave on
         *    which we intend to run this job instance on. For this, we depend
         *    on the site/location name property given to the resource and pair
         *    the job that has an appropriate / matching label. The approach
         *    we are taking is that if Node/Slave label we want to use has a
         *    colon terminated prefix, then the site location for the resource
         *    is the given prefix.
         *    e.g. if the Node label to use is _HQ:rkslave, that means we must
         *    restrict our choice of resource selection to site _HQ. Similarly,
         *    a node / slave label of _COLO:rkslave implies siteName  _COLO.
         *    a node / slave label of _SJC:rkslave implies siteName  _SJC.
         *
         *    If no location prefix is found, we will use all listed resources
         *    to chose from. That is, no restriction of site.
         * */

        List<ParametersAction> paramActions =
            item.getActions(ParametersAction.class);
        String siteLocation = null;
        for (ParametersAction paramAction : paramActions) {
            ParameterValue rsrcLabel =
                paramAction.getParameter("LOCKABLE_RESOURCE_LABEL");
            if(rsrcLabel instanceof StringParameterValue) {
                resources.label = ((StringParameterValue) rsrcLabel).value;
                LOGGER.finest("Use lockable resource label "
                              + resources.label);
            }
            List<ParameterValue> itemParams = paramAction.getParameters();
            for (ParameterValue pv : itemParams) {
                if(pv instanceof LabelParameterValue) {
                    String[] nodelabel =
                        ((LabelParameterValue) pv).getLabel().split(":");
                    if (nodelabel.length > 1) {
                        siteLocation = nodelabel[0];
                        LOGGER.finest("Use slaves with label that begin with "
                                      + siteLocation + ":");
                        break;
                    }
                }
            }
        }

        LOGGER.finest(project.getName() +
            " - Trying to get resources with these details: " + resources);

        if (LockableResourcesManager.get().getUseBodega()) {
            BodegaService bodega =
                LockableResourcesManager.get().getBodegaService();
            BodegaOrderAction bodegaOrderAction =
                item.getAction(BodegaOrderAction.class);
            if (bodegaOrderAction == null) {
                try {
                    LOGGER.log(
                        Level.FINER,
                        "No Bodega order found for queue item " +
                        item.getId() + ", so creating one.");
                    Order requestedOrder = new Order();
                    StringBuffer variablesNotes = new StringBuffer();
                    requestedOrder.status = Order.Status.OPEN;
                    if (resources.bodegaItemRequirements != null &&
                        !resources.bodegaItemRequirements.isEmpty()) {
                        String itemRequirements =
                            replaceEnvironmentVariablesInItemRequirements(
                                project,
                                resources.bodegaItemRequirements,
                                paramActions,
                                variablesNotes);
                        LOGGER.log(
                            Level.FINER,
                            "Placing Bodega order for queue item " +
                            item.getId() + " with item requirements: " +
                            itemRequirements);
                        requestedOrder.items = itemRequirements;
                    } else {
                        LOGGER.log(
                            Level.FINER,
                            "Placing Bodega order for queue item " +
                            item.getId() +
                            " using legacy lockable resource label.");
                        Map<String, OrderItem> orderItems =
                            getOrderItems(resources);
                        requestedOrder.setItems(getOrderItems(resources));
                    }
                    String locationNotes = setDefaultLocations(requestedOrder);
                    String networkNotes = setDefaultNetworks(requestedOrder);
                    requestedOrder.timeLimit = "01:30:00";
                    requestedOrder.comment =
                        "For Jenkins queue item " +
                        Utils.getQueueItemDescription(item) +
                        "\n\n" + variablesNotes.toString() + locationNotes +
                        networkNotes;
                    Order order = BodegaServiceUtil.getResponse(
                        bodega.createOrder(requestedOrder));
                    LOGGER.log(
                        Level.FINE,
                        "Placed Bodega order for queue item " + item.getId() +
                        ": " + order);
                    bodegaOrderAction = new BodegaOrderAction(
                      order.sid,
                      System.currentTimeMillis());
                    item.addAction(bodegaOrderAction);
                } catch (Exception e) {
                    LOGGER.log(
                        Level.WARNING,
                        "Failed to place Bodega order for queue item " +
                        item.getId() + ", so keeping the item blocked.",
                        e);
                    return new BecauseBodegaOrderSid(null);
                }
            }

            String orderSid = bodegaOrderAction.orderSid;
            Order order = null;
            try {
                order = BodegaServiceUtil.getResponse(
                    bodega.getOrder(orderSid));
                LOGGER.log(
                    Level.FINEST, "Checking status of Bodega order: " + order);
                if (order.status == Order.Status.FULFILLED) {
                    LOGGER.finest(
                        "Bodega order SID " + orderSid +
                        " is fulfilled, so queue item " + item.getId() +
                        " is ready to run.");
                    addFulfilledItemsToRequiredVar(item, resources, order);
                    assignSlaveForFulfilledItems(item, order);
                    addBodegaOrderUrlAsParameter(item, order.url);
                    return null;
                } else if (order.status == Order.Status.CLOSED) {
                    // If the order has been closed (typically for going over
                    // its time limit), this queue item will  never really be
                    // able to run. However, if we abort the queue item from
                    // here, it will just be silently deleted and the user
                    // wouldn't see any indication of this abnormal event in
                    // the Jenkins UI. So allow it to run, then later abort
                    // it with an error message in the build console output.
                    LOGGER.finest(
                        "Bodega order SID " + orderSid +
                        " is closed, so queue item " + item.getId() +
                        " should try to run and abort with a " +
                        "visible error.");
                    if(item.isBlocked() && !item.isStuck()) {
                        /*
                            On jenkins instances with only dynamic slaves,
                            this code executes in a loop (presumably till the
                            jenkins instance is shutdown or the build is
                            aborted)
                            On returning null in the first iteration of
                            the loop, the build item goes from state
                            blocked -> stuck.
                            Thus, we capture the stat only when it is in blocked
                            state (thereby capturing it only once)
                        */
                        publishOrderClosedStats(item);
                    }
                    return null;
                }
                LOGGER.finest(
                    "Bodega order SID " + orderSid +
                    " is not fulfilled, so queue item " + item.getId() +
                    " is still waiting.");
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to check status of Bodega order " + orderSid +
                    "for queue item " + item.getId() +
                    ", so keeping the item blocked.",
                    e);
                publishFailureStats(e);
            }
            if (order != null){
                return new BecauseBodegaOrder(order);
            }
            return new BecauseBodegaOrderSid(orderSid);

        }

        if (resources.required.isEmpty() && resources.label.isEmpty())
            return null;

        int resourceNumber = resources.getRequiredNumber();
        if (resourceNumber > 0 || !resources.label.isEmpty()) {
            Map<String, Object> params = new HashMap<String, Object>();
            if (item.task instanceof MatrixConfiguration) {
                MatrixConfiguration matrix = (MatrixConfiguration) item.task;
                params.putAll(matrix.getCombination());
            }

            List<LockableResource> selected =
                LockableResourcesManager.get().queue(resources,
                                                     item.getId(),
                                                     project.getFullName(),
                                                     resourceNumber,
                                                     params,
                                                     siteLocation,
                                                     LOGGER);
            if (selected != null) {
                /* At this stage, we have 'selected' a set of co-located (i.e.
                 * common siteName) resources for the given job. If the slave's
                 * label to use is not already defined / determined, we need to
                 * associate one. The getAssignedLabel method gives a read-only
                 * detail of the nodeLabel to use. In order to change the label
                 * we depend on nodelabelparameter plugin which implements the
                 * setAssignedLabel extension point for us.
                 *
                 * So, if we have not already found the siteLocation for slave,
                 * this is the place to determine and define as per the site of
                 * selected resources.
                 *
                 * Possible scenarios :-
                 * 1. The job config has not indicated any preference of any
                 *    node label. In this case, we assign the default choice of
                 *    <Resource-Site-Location>:rkslave
                 * 2. The job is configured to use slave with label 'XXX'.
                 *    XXX does not have a colon terminated location prefix.
                 *    Change the preferred label to be
                 *    "<resource-site-location>:XXX"
                 *    The way to change the preferred label is to attach a
                 *    ParametersAction that has one of the entries to be of
                 *    type 'LabelParameterValue'
                 */

                String loc = selected.get(0).getSiteName();
                if (siteLocation == null) {
                    String useLabel = null;
                    if (item.getAssignedLabel() == null) {
                        useLabel = loc + ":rkslave";
                        LOGGER.finest("Assigning default label : " + useLabel);
                    } else {
                        String currLabel =  item.getAssignedLabel().getName();
                        if (!currLabel.startsWith(loc + ":")) {
                            useLabel = loc + ":" + currLabel;
                        // } else {
                        //    We have already gotten the location name. Nothing
                        //    more to do.
                        // }
                        }
                    }
                    if (useLabel != null) {
                        LOGGER.finest("Assigning label: " + useLabel);
                        List<ParameterValue> locParam =
                            new ArrayList<ParameterValue>();
                        LabelParameterValue slaveLabel =
                            new LabelParameterValue("SLAVE_LABEL", useLabel);
                        // Dont know why this step is necessary. TBD.
                        slaveLabel.setLabel(useLabel);
                        locParam.add(slaveLabel);
                        item.addAction(new ParametersAction(locParam));
                        LOGGER.finest("Changed Item " + item.getId() +
                                      " label to " + item.getAssignedLabel());
                    }
                }
                LOGGER.finest("Item #" + item.getId()
                              + " can proceed to run on a slave wth label "
                              + item.getAssignedLabel());
                return null;
            } else {
                LOGGER.finest(project.getName() + " waiting for resources");
                return new BecauseResourcesLocked(resources);
            }
        } else {
            if (LockableResourcesManager.get().queue(resources.required,
                                                     item.getId())) {
                LOGGER.finest(project.getName()
                              + " reserved resources " + resources.required);
                return null;
            } else {
                LOGGER.finest(project.getName() + " waiting for resources "
                    + resources.required);
                return new BecauseResourcesLocked(resources);
            }
        }
    }

    private void publishOrderClosedStats(Queue.Item item) {
        try {
            final StatsDClient statsDClient =
              LockableResourcesManager.get().getOrCreateStatsdClient();
            final String orderClosedStat =
              String.format("%s.order_closed", item.task.getName());
            statsDClient.increment(orderClosedStat);
        } catch (Exception any) {
            LOGGER.log(
              Level.WARNING,
              "Could not publish order close stats",
              any);
        }
    }

    private void publishFailureStats(Exception e) {
        try {
            final StatsDClient statsDClient =
              LockableResourcesManager.get().getOrCreateStatsdClient();
            String statName = String.format(
              "bodega_fetch_failed.%s",
              e.getClass().getSimpleName());
            LOGGER.log(Level.WARNING,"Incrementing {0} metric", statName);
            statsDClient.increment(statName);
        } catch (Exception any) {
            LOGGER.log(Level.WARNING,"Could not publish failure stats", any);
        }
    }

    private Map<String, OrderItem> getOrderItems(
        LockableResourcesStruct requiredResources) {

        List<OrderItem> orderItemsList = getOrderItemsList(requiredResources);
        Map<String, OrderItem> orderItems = new HashMap<String, OrderItem>();
        for (int i = 0; i < orderItemsList.size(); i++) {
            String nickname = "resource_" + (i + 1);
            OrderItem orderItem = orderItemsList.get(i);
            orderItems.put(nickname, orderItem);
        }

        return orderItems;
    }

    private List<OrderItem> getOrderItemsList(
        LockableResourcesStruct requiredResources) {

        List<OrderItem> orderItemsList = new ArrayList<OrderItem>();

        for (LockableResource specificRequiredResource :
             requiredResources.required) {
            orderItemsList.add(
                getOrderItemForSpecificResource(specificRequiredResource));
        }

        if (requiredResources.label != null &&
            !requiredResources.label.isEmpty()) {
            for (int i = 0; i < requiredResources.getRequiredNumber(); i++) {
                orderItemsList.add(
                    getOrderItemForLabel(requiredResources.label));
            }
        }

        return orderItemsList;
    }

    private OrderItem getOrderItemForSpecificResource(
        LockableResource resource) {

        OrderItem orderItem = new OrderItem();
        if (resource.getGearType().equals(
                OrderItem.Type.RELEASE_QUAL_BATON.toString())) {

            orderItem.type = OrderItem.Type.RELEASE_QUAL_BATON;
            ReleaseQualBaton.Requirements requirements =
                new ReleaseQualBaton.Requirements();
            requirements.sid = resource.getBodegaSid();
            orderItem.requirements = requirements;
        } else if (resource.getGearType().equals(
            OrderItem.Type.RKTEST_YML.toString())) {

            Gson gson = BodegaServiceUtil.getGson();
            orderItem.type = OrderItem.Type.RKTEST_YML;
            RktestYml.Requirements requirements =
                new RktestYml.Requirements();
            requirements.sid = resource.getBodegaSid();
            requirements.location = gson.fromJson(
                "\"" + resource.getSiteName() + "\"", RktestYml.Location.class);
            orderItem.requirements = requirements;
        } else {
            throw new UnsupportedOperationException(
                "Can't create order item for unrecognized type \"" +
                resource.getGearType() + "\"");
        }

        return orderItem;
    }

    private OrderItem getOrderItemForLabel(String label) {
        OrderItem orderItem = new OrderItem();

        if (label.equals("release_qualification_baton")) {
            orderItem.type = OrderItem.Type.RELEASE_QUAL_BATON;
            orderItem.requirements = new ReleaseQualBaton.Requirements();
        } else {
            orderItem.type = OrderItem.Type.RKTEST_YML;
            RktestYml.Requirements requirements = new RktestYml.Requirements();
            setRktestYmlRequirementsForLabel(requirements, label);
            orderItem.requirements = requirements;
        }

        return orderItem;
    }

    private String replaceEnvironmentVariablesInItemRequirements(
        AbstractProject<?, ?> project,
        String bodegaItemRequirements, List<ParametersAction> paramActions,
        StringBuffer variablesNotes) {
        /* We are implementing our own macros/templates in the item
         * requirements. The item requirements are defined in the
         * ansible YAML templates. This approach is confusing and
         * unintuitive so this will most likely be changed in the future
         * to a cleaner solution.
         */

        String itemRequirements = bodegaItemRequirements;

        if (itemRequirements.contains("${ARTIFACTS_URL_TO_USE}")) {
            LOGGER.finest("Found string '${ARTIFACTS_URL_TO_USE}' in " +
                          "item requirements so attempt to replace it.");
            String artifactsUrlToUse = "";
            String artifactsUrlNote = null;

            for (ParametersAction paramAction : paramActions) {
                ParameterValue artifactsLabel =
                    paramAction.getParameter("ARTIFACTS_URL_TO_USE");
                ParameterValue buildNumberLabel =
                    paramAction.getParameter("BUILD_NUMBER_TO_USE");
                ParameterValue buildSelectorJobLabel =
                    paramAction.getParameter("BUILD_SELECTOR_JOB");
                String label = ((StringParameterValue) artifactsLabel).value;
                String buildNumber =
                    ((StringParameterValue) buildNumberLabel).value;
                String buildSelectorJob =
                    ((StringParameterValue) buildSelectorJobLabel).value;
                if (label.length() != 0) {
                    LOGGER.finest("ARTIFACTS_URL_TO_USE has a value of '" +
                                  label + "' so use it in the item " +
                                  "requirements.");
                    artifactsUrlNote =
                        "the ARTIFACTS_URL_TO_USE label value '" + label + "'";
                    artifactsUrlToUse = label;
                } else if (buildNumber.length() != 0 &&
                           buildSelectorJob.length() != 0) {
                    LOGGER.finest("Looking for artifacts.json artifact in  " +
                                  "from the BUILD_NUMBER (" + buildNumber +
                                  ") and BUILD_SELECTOR_JOB (" +
                                  buildSelectorJob + ").");
                    Run<?, ?> run = getRun(buildSelectorJob, buildNumber);
                    if (run != null) {
                        label = getArtifactsUrlFromRun(run);
                        if (label != null && !label.isEmpty()) {
                            artifactsUrlNote =
                                "the '" + label + "' found in the build of " +
                                "BUILD_SELECTOR_JOB='" + buildSelectorJob +
                                "' and BUILD_NUMBER='" + buildNumber + "'";
                            artifactsUrlToUse = label;
                        } else {
                            LOGGER.warning(
                                "No artifacts.json found in build of " +
                                "BUILD_SELECTOR_JOB='" + buildSelectorJob +
                                "' and BUILD_NUMBER='" + buildNumber +
                                "' so will fall back to an empty default.");
                            artifactsUrlNote =
                                "a default string '" + artifactsUrlToUse +
                                "' because no artifacts.json was found in " +
                                "build of BUILD_SELECTOR_JOB='" +
                                buildSelectorJob + "' and BUILD_NUMBER='" +
                                buildNumber;
                        }
                    } else {
                        LOGGER.warning(
                            "No run found for BUILD_SELECTOR_JOB='" +
                            buildSelectorJob + "' and BUILD_NUMBER='" +
                            buildNumber +
                            "' so will fall back to an empty default.");
                        artifactsUrlNote =
                            "a default string '" + artifactsUrlToUse +
                            "' because no build of BUILD_SELECTOR_JOB='" +
                            buildSelectorJob + "' and BUILD_NUMBER='" +
                            buildNumber + "' was found.";
                    }
                } else {
                    LOGGER.warning("Could not get a valid URL for " +
                                   "ARTIFACTS_URL_TO_USE so using an empty " +
                                   "string.");
                    artifactsUrlNote =
                        "a default string: '" + artifactsUrlToUse + "'";
                }
            }

            itemRequirements = itemRequirements.replaceAll(
                "\\$\\{ARTIFACTS_URL_TO_USE\\}", artifactsUrlToUse);
            variablesNotes.append(
                "Item requirements had '${ARTIFACTS_URL_TO_USE}' " +
                "substituted with " + artifactsUrlNote + ".\n\n");
        }

        if (itemRequirements.contains("${SD_DEV_BOOTSTRAP_HASH}")) {
            LOGGER.finest("Found string '${SD_DEV_BOOTSTRAP_HASH}' in " +
                          "item requirements so attempt to replace it.");
            String artifactsUrlToUse = null;
            String buildNumber = null;
            String buildSelectorJob = null;
            String diffId = null;
            for (ParametersAction paramAction : paramActions) {
                ParameterValue artifactsLabel =
                    paramAction.getParameter("ARTIFACTS_URL_TO_USE");
                ParameterValue buildNumberLabel =
                    paramAction.getParameter("BUILD_NUMBER_TO_USE");
                ParameterValue buildSelectorJobLabel =
                    paramAction.getParameter("BUILD_SELECTOR_JOB");
                ParameterValue diffIdLabel =
                    paramAction.getParameter("DIFF_ID");

                if (artifactsLabel != null) {
                    artifactsUrlToUse =
                        ((StringParameterValue) artifactsLabel).value;
                }
                if (buildNumberLabel != null) {
                    buildNumber =
                        ((StringParameterValue) buildNumberLabel).value;
                }
                if (buildSelectorJobLabel != null) {
                    buildSelectorJob =
                        ((StringParameterValue) buildSelectorJobLabel).value;
                }
                if (diffIdLabel != null) {
                    diffId = ((StringParameterValue) diffIdLabel).value;
                }
            }

            StringBuffer sdDevHashNote = new StringBuffer();
            String sdDevBootstrapHash = determineSdDevBootstrapHash(
                project, diffId,
                artifactsUrlToUse, buildNumber, buildSelectorJob,
                sdDevHashNote);
            LOGGER.finest(
                "Replacing all \\$\\{SD_DEV_BOOTSTRAP_HASH\\} in item " +
                "requirements with '"+ sdDevBootstrapHash + "'.");
            itemRequirements = itemRequirements.replaceAll(
                "\\$\\{SD_DEV_BOOTSTRAP_HASH\\}", sdDevBootstrapHash);
            variablesNotes.append(
                "Item requirements had '${SD_DEV_BOOTSTRAP_HASH}' " +
                "substituted with " + sdDevHashNote.toString() + ".\n\n");
        }

        return itemRequirements;
    }

    private String determineSdDevBootstrapHash(
        AbstractProject<?, ?> project,
        String diffId,
        String artifactsUrlToUse,
        String buildNumber,
        String buildSelectorJob,
        StringBuffer sdDevHashNote) {

        SCM scm = project.getScm();
        if (scm instanceof GitSCM) {
            LOGGER.finest(
                "Project " + project.getName() + " is configured to use " +
                "Git SCM, so it will be checking out Git source. We will " +
                "determine the appropriate sd_dev_bootstrap hash version " +
                "from Git.");
            return determineSdDevBootstrapHashFromGit(
                ((GitSCM) scm), diffId, sdDevHashNote);
        } else if (scm instanceof NullSCM || scm == null) {
            LOGGER.finest(
                "Project " + project.getName() + " is not configured to use " +
                "SCM, so it will probably be consuming artifacts. We will " +
                "determine the appropriate sd_dev_bootstrap hash version " +
                "from artifact metadata.");
            return determineSdDevBootstrapHashFromArtifacts(
                artifactsUrlToUse, buildSelectorJob, buildNumber,
                sdDevHashNote);
        } else {
            LOGGER.finest(
                "Project " + project.getName() + " is configured to use " +
                "SCM, so it will be checking out source. However, we don't " +
                "recognize/support " + scm.toString() + ", so we must fall " +
                "back to choosing the global default sd_dev_bootstrap hash.");
            sdDevHashNote.append(
                "global default sd_dev_bootstrap hash of '" +
                defaultSdDevBootstrapHash + "' since we don't support " +
                "the SCM configured on the job.");
            return defaultSdDevBootstrapHash;
        }
    }

    private String determineSdDevBootstrapHashFromGit(
        GitSCM gitScm, String diffId, StringBuffer sdDevHashNote) {

        List<UserRemoteConfig> userRemoteConfigs =
            gitScm.getUserRemoteConfigs();
        List<BranchSpec> branchSpecs = gitScm.getBranches();
        if (!(userRemoteConfigs.size() > 0 && branchSpecs.size() > 0)) {
            LOGGER.finest(
                "Missing repository URL and/or branch for Git SCM " +
                "configuration, so fall back to choosing global default " +
                "sd_dev_bootstrap hash " + defaultSdDevBootstrapHash);
            sdDevHashNote.append(
                "global default sd_dev_bootstrap hash version '" +
                defaultSdDevBootstrapHash + "' since we're missing the " +
                "Git repository URL and/or branch");
            return defaultSdDevBootstrapHash;
        }

        String repoUrl = userRemoteConfigs.get(0).getUrl();
        String branch = branchSpecs.get(0).getName();
        LOGGER.finest(
            "Determining sd_dev_bootstrap hash from Git SCM configuration " +
            "that specifies repository URL " + repoUrl + " and branch " +
            branch + " while this build's DIFF_ID value is " + diffId);

        String gitRef = null;
        String gitRefSource = null;
        if (diffId != null && !diffId.isEmpty()) {
            try {
                ConduitCredentials credentials = Jenkins.getInstance()
                    .getDescriptorByType(
                        PhabricatorBuildWrapperDescriptor.class)
                    .getCredentials(null);
                LOGGER.finest(
                    "Getting information about DIFF_ID=" + diffId +
                    " from Phabricator at " + credentials.getUrl() +
                    " to determine its base commit.");
                ConduitAPIClient conduit = new ConduitAPIClient(
                    credentials.getUrl(),
                    credentials.getToken().getPlainText());
                JSONObject diffResponse = conduit.perform(
                    "differential.getdiff",
                    new JSONObject().element("diff_id", diffId));
                gitRef = diffResponse
                    .getJSONObject("result")
                    .getString("sourceControlBaseRevision");
                gitRefSource =
                    "sourceControlBaseRevision of Phabricator DIFF_ID='" +
                    diffId + "'";
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to get information about DIFF_ID=" + diffId +
                    " from Phabricator. We will have to choose the global " +
                    " default sd_dev_bootstrap hash, which could be wrong.",
                    e);
                return defaultSdDevBootstrapHash;
            }
        } else {
            // There's a possible race condition here that we determine the
            // sd_dev bootstrap hash from the top of the branch now, but by
            // the time the job runs and actually clones from Git, the branch
            // and sd_dev bootstrap hash may have been updated. Ideally we
            // would resolve the branch to a fixed commit hash now and make the
            // running job clone the same hash, but we don't know if that's
            // possible. Fortunately, this scenario should be somewhat rare and
            // our build jobs (namely Build_CDM) are flexible enough to work
            // off older sd_dev versions by running another sd_dev_boostrap.
            if (branch.startsWith("origin/")) {
                gitRef = branch.substring(branch.indexOf('/') + 1);
            } else {
                gitRef = branch;
            }
            gitRefSource =
                "branch '" + branch +
                "' configured on the job's Git SCM settings";
        }

        String sdDevBootstrapHash = null;
        LOGGER.fine(
            "Will peek at deployment/.sd_dev_bootstrap_hash file contents " +
            "in Git repository " + repoUrl + " at revision " + gitRef);
        try {
            List<StringCredentials> credentials =
                CredentialsProvider.lookupCredentials(
                    StringCredentials.class, (AbstractProject) null, null);
            StringCredentials credential =
                CredentialsMatchers.firstOrDefault(
                    credentials,
                    CredentialsMatchers.allOf(
                        CredentialsMatchers.withId("GITHUB_API_TOKEN")),
                    null);
            if (credential == null) {
                throw new Exception("No GITHUB_API_TOKEN found.");
            }

            GitHub github = GitHub.connectUsingOAuth(
                credential.getSecret().getPlainText());
            List<String> repoComponents = Arrays.asList(repoUrl.split(":"));
            if (repoComponents.size() < 2 ||
                !repoComponents.get(0).contains("github.com")) {
                throw new UnsupportedOperationException(
                    "Repository URL '" + repoUrl + "' does not appear to be " +
                    "a Github repository. Only Github repositories are " +
                    "supported because we peek at file contents using the " +
                    "Github API.");
            }
            String repoName = repoComponents.get(1);
            if (repoName.endsWith(".git")) {
                repoName = repoName.substring(0, repoName.lastIndexOf('.'));
            }
            GHRepository repository = github.getRepository(repoName);
            GHContent content = repository.getFileContent(
                "deployment/.sd_dev_bootstrap_hash", gitRef);
            sdDevBootstrapHash = content.getContent().trim();
            LOGGER.fine(
                "Got deployment/.sd_dev_bootstrap_hash contents from " +
                "Github repository " + repoName + " at revision " + gitRef +
                ": "+ sdDevBootstrapHash);
            sdDevHashNote.append(
                "contents of deployment/.sd_dev_bootstrap_hash file peeked " +
                "from Github repository '" + repoUrl + "' revision '" +
                gitRef + "' determined by " + gitRefSource);
        } catch (Exception e) {
            LOGGER.log(
                Level.WARNING,
                "Failed to peek at deployment/.sd_dev_bootstrap_hash file " +
                "contents in Github. We will have to choose the global " +
                "default sd_dev_bootstrap hash, which could be wrong.",
                e);
            sdDevBootstrapHash = defaultSdDevBootstrapHash;
            sdDevHashNote.append(
                "global default sd_dev_bootstrap_hash of '" +
                defaultSdDevBootstrapHash + "' since we failed to peek " +
                "at the deployment/.sd_dev_bootstrap_hash file contents " +
                "in Github");
        }

        return sdDevBootstrapHash;
    }

    private String determineSdDevBootstrapHashFromArtifacts(
        String artifactsUrlToUse, String buildSelectorJob, String buildNumber,
        StringBuffer sdDevHashNote) {

        // Look for a Tivan-style artifacts URL which will have enough
        // information to determine the sd_dev version hash.
        String artifactsUrl = null;
        String artifactsUrlSource = null;
        Run<?, ?> selectedRun = null;
        if (artifactsUrlToUse != null && !artifactsUrlToUse.isEmpty()) {
            LOGGER.finest("Artifacts URL given: " + artifactsUrlToUse);
            // In the most modern ideal case, we are directly consuming a
            // Tivan-style artifacts URL.
            artifactsUrl = artifactsUrlToUse;
            artifactsUrlSource =
                "ARTIFACTS_URL_TO_USE value '" + artifactsUrlToUse + "'";
        } else if (buildSelectorJob != null && !buildSelectorJob.isEmpty() &&
                   buildNumber != null && !buildNumber.isEmpty()) {
            // Otherwise we might find an artifacts.json file in the selected
            // build's artifacts.
            selectedRun = getRun(buildSelectorJob, buildNumber);

            // Now try to find an artifacts.json artifact. Even if not found
            // though, knowing the selectedRun may be useful for fallbacks.
            if (selectedRun != null) {
                artifactsUrl = getArtifactsUrlFromRun(selectedRun);
                if (artifactsUrl != null && !artifactsUrl.isEmpty()) {
                    LOGGER.finest(
                        "Determined artifacts URL from run: " + artifactsUrl);
                    artifactsUrlSource =
                        "artifacts.json in build at BUILD_SELECTOR_JOB='" +
                        buildSelectorJob + "' and BUILD_NUMBER='" +
                        buildNumber + "'";
                } else {
                    LOGGER.finest(
                        "No 'artifacts.json' artifact found in build '" +
                        buildNumber + "' of job '" + buildSelectorJob + "'.");
                }
            }
        } else {
            LOGGER.finest(
                "Nothing was provided for determing sd_dev hash. We'll " +
                "probably have to choose the global default one.");
        }

        // Look for sd_dev version hash explicitly recommended by Tivan-style
        // artifacts, if available.
        String sdDevBootstrapHash = null;
        String cdmVersion = null;
        String cdmVersionSource = null;
        if (artifactsUrl != null && !artifactsUrl.isEmpty()) {
            // Get sd_dev_hash if exists, otherwise populate cdmVersion
            LOGGER.finest(
                "Trying to get sd_dev_bootstrap hash and/or CDM version " +
                "from Tivan-style artifacts metadata at " + artifactsUrl);
            Map<String, Artifact> artifacts = null;
            try {
                URL url = new URL(artifactsUrl);
                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(url.openStream()));
                StringBuilder artifactsJson = new StringBuilder();
                String line = null;
                while ((line = reader.readLine()) != null) {
                    artifactsJson.append(line);
                }

                Gson gson = BodegaServiceUtil.getGson();
                artifacts = gson.fromJson(
                    artifactsJson.toString(),
                    (new TypeToken<Map<String, Artifact>>() {}).getType());
            } catch (Exception e) {
                LOGGER.log(
                    Level.WARNING,
                    "Failed to read Tivan-style artifacts metadata from '" +
                    artifactsUrl + "'. We will probably have to fall back " +
                    "to the default sd_dev version.",
                    e);
            }

            if (artifacts != null &&
                artifacts.containsKey("cdm_internal_tarball")) {
                Artifact cdmInternalTarball = artifacts.get(
                    "cdm_internal_tarball");
                LOGGER.finest(
                    "Got cdm_internal_tarball information from artifacts " +
                    "at '" + artifactsUrl + "': " + cdmInternalTarball);
                cdmVersion = cdmInternalTarball.version;
                cdmVersionSource =
                    "Tivan-style artifacts metadata from " +
                    artifactsUrlSource;
                LOGGER.finest(
                    "Determined CDM version to be '" + cdmVersion +
                    "' from cdm_internal_tarball.version in artifacts at '" +
                    artifactsUrl + "'.");
                if (cdmInternalTarball.sdDevBootstrapHash != null &&
                    !cdmInternalTarball.sdDevBootstrapHash.isEmpty()) {
                    sdDevBootstrapHash = cdmInternalTarball.sdDevBootstrapHash;
                    sdDevHashNote.append(
                        "cdm_internal_tarball.sd_dev_bootstrap_hash in " +
                        "Tivan-style artifacts metadata from " +
                        artifactsUrlSource);
                    LOGGER.fine(
                        "Determined sd_dev_bootstrap hash value '" +
                        sdDevBootstrapHash +
                        "' from cdm_internal_tarball.sd_dev_bootstrap_hash " +
                        "value from artifacts at '" + artifactsUrl + "'");
                } else {
                    LOGGER.fine(
                        "No cdm_internal_tarball.sd_dev_bootstrap_hash " +
                        "recommendation found in artifacts at '" +
                        artifactsUrl + "'. Will fall back to other means of " +
                        "guessing an sd_dev version.");
                }
            } else {
                LOGGER.finest(
                    "No cdm_internal_tarball found in artifacts at '" +
                    artifactsUrl + "'. Will fall back to other means of " +
                    "guessing an sd_dev version.");
            }
        } else if (selectedRun != null) {
            // Populate cdmVersion
            LOGGER.finest(
                "Trying to get get CDM version from artifacts in run at " +
                "BUILD_SELECTOR_JOB=" + buildSelectorJob +
                " and BUILD_NUMBER=" + buildNumber);
            for (Run.Artifact artifact : selectedRun.getArtifacts()) {
                String fileName = artifact.getFileName();
                String prefix = "internal-rubrik-";
                String suffix = ".tar.gz";
                if (fileName.startsWith(prefix) && fileName.endsWith(suffix)) {
                    cdmVersion = fileName.substring(
                        prefix.length(), fileName.length() - suffix.length());
                    cdmVersionSource =
                        "recognizing internal-rubrik-* filename from " +
                        "artifacts of build at BUILD_SELECTOR_JOB='" +
                        buildSelectorJob + "' and BUILD_NUMBER='" +
                        buildNumber + "'";
                    LOGGER.finest(
                        "Via artifact " + fileName + ", discovered CDM " +
                        "version to be " + cdmVersion);
                }
            }

            if (cdmVersion == null || cdmVersion.isEmpty()) {
                LOGGER.finest(
                    "Could not find CDM version from artifacts in run at " +
                    "BUILD_SELECTOR_JOB=" + buildSelectorJob +
                    "and BUILD_NUMBER=" + buildNumber + ". We will probably " +
                    "have to fall back to choosing a default " +
                    "sd_dev_bootstrap hash.");
            }
        } else {
            LOGGER.finest(
                "We have no information for determining an sd_dev_bootstrap " +
                "hash. We will probably have to fall back to choosing a " +
                "default one.");
        }

        // Haven't figured out an sd_dev version by now, so fall back to
        // educated guesses.
        if (sdDevBootstrapHash == null || sdDevBootstrapHash.isEmpty()) {
            if (cdmVersion != null && !cdmVersion.isEmpty()) {
                LOGGER.finest(
                    "Guesstimating an appropriate sd_dev_bootstrap hash " +
                    "based on CDM version " + cdmVersion + ".");
                // The more educated guess is based on the CDM version.
                sdDevBootstrapHash =
                    determineSdDevBootstrapHashFromCdmVersion(cdmVersion);
                sdDevHashNote.append(
                    "guesstimated sd_dev_bootstrap hash for CDM version '" +
                    cdmVersion + "' from " + cdmVersionSource);
            } else {
                // If even a CDM version is unavailable, we have no choice but
                // to use our worst guess, the global default sd_dev version
                // hash.
                LOGGER.finest(
                    "No sd_dev_bootstrap_hash or CDM version was " +
                    "determined, so falling back to the global default " +
                    "sd_dev_bootstrap hash version " +
                    defaultSdDevBootstrapHash);
                sdDevBootstrapHash = defaultSdDevBootstrapHash;
                sdDevHashNote.append(
                    "global default sd_dev_bootstrap hash version '" +
                    defaultSdDevBootstrapHash + "' because no " +
                    "sd_dev_bootstrap hash or CDM version were discovered");
            }
        }

        return sdDevBootstrapHash;
    }

    private String getArtifactsUrlFromRun(Run<?, ?> run) {
        for (Run.Artifact artifact : run.getArtifacts()) {
            if (artifact.relativePath.equals("artifacts.json")) {
                return Jenkins.getInstance().getRootUrl() +
                    run.getUrl() + "artifact/" + artifact.relativePath;
            }
        }

        return null;
    }

    private Run<?, ?> getRun(String buildSelectorJob, String buildNumber) {
        AbstractProject<?, ?> project =
            Jenkins.getInstance().getItemByFullName(
                buildSelectorJob, AbstractProject.class);
        if (project == null) {
            LOGGER.log(
                Level.WARNING,
                "Job named '" + buildSelectorJob + "' not found, so " +
                "unable to determine sd_dev bootstrap hash. Falling " +
                "back to default.");
            return null;
        }

        String buildNum = buildNumber.trim();
        Run<?, ?> run = project.getBuild(buildNum);
        if (run == null) {
            LOGGER.log(
                Level.WARNING,
                "Build '" + buildNum + "' in job '" + buildSelectorJob +
                "' not found, so unable to determine sd_dev bootstrap " +
                "hash. Falling back to default.");
            return null;
        }

        return run;
    }

    private String determineSdDevBootstrapHashFromCdmVersion(
        String cdmVersion) {

        if (cdmVersion.startsWith("3.")) {
            LOGGER.finest(
                "CDM version '" + cdmVersion + "' appears to be 3.x, so use " +
                "the sd_dev bootstrap hash compatible with 3.x.");
            return "4f522b5d0084ef783371506cfb35103ab3a31adf";
        } else if (cdmVersion.startsWith("4.")) {
            LOGGER.finest(
                "CDM version '" + cdmVersion + "' appears to be 4.x and " +
                "and likely older than builds that explicitly recommend an " +
                "sd_dev_bootstrap_hash value, so use the sd_dev bootstrap " +
                "hash compatible with older 4.x.");
            return "8a72da80bb385f436c12b2d0e0488f177b5fde34";
        } else {
            LOGGER.finest(
                "We do not have a heuristic for determining the sd_dev " +
                "bootstrap hash for CDM version '" + cdmVersion + "', so " +
                "use the global default sd_dev bootstrap hash.");
            return defaultSdDevBootstrapHash;
        }
    }

    private void setRktestYmlRequirementsForLabel(
        RktestYml.Requirements requirements, String label) {

        String labelWithoutLocation = null;
        if (label.endsWith("_COLO")) {
            labelWithoutLocation = label.substring(0, label.lastIndexOf('_'));
            requirements.location = RktestYml.Location.COLO;
        } else if (label.endsWith("_HQ")) {
            labelWithoutLocation = label.substring(0, label.lastIndexOf('_'));
            requirements.location = RktestYml.Location.HQ;
        } else {
            labelWithoutLocation = label;
        }

        if (labelWithoutLocation.equals("benchmarking")) {
            requirements.benchmarking = true;
        } else if (labelWithoutLocation.equals("DYNAMICPOD")) {
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("edge_dynapod")) {
            requirements.platform = RktestYml.Platform.DYNAPOD_ROBO;
        } else if (labelWithoutLocation.equals("edge_dynapod_mssql")) {
            requirements.msSql = true;
            requirements.platform = RktestYml.Platform.DYNAPOD_ROBO;
        } else if (labelWithoutLocation.equals("encrypted")) {
            requirements.encrypted = true;
        } else if (labelWithoutLocation.equals("hyperv_2016")) {
            requirements.hyperv2016 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("linux_agent")) {
            requirements.linuxAgent = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("linux_agent_all_versions")) {
            requirements.linuxAgentAllVersions = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("manufacturable")) {
            requirements.manufacturable = true;
        } else if (labelWithoutLocation.equals("model_r6xx")) {
            requirements.model_r6xx = true;
        } else if (labelWithoutLocation.equals("mssql")) {
            requirements.msSql = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("nonstandardbrik")) {
        } else if (labelWithoutLocation.equals("PROD_BRIK")) {
            requirements.platform = RktestYml.Platform.PROD_BRIK;
        } else if (labelWithoutLocation.equals("prod_pool")) {
            requirements.platform = RktestYml.Platform.PROD_BRIK;
        } else if (labelWithoutLocation.equals("prod_tpm")) {
            requirements.platform = RktestYml.Platform.PROD_BRIK;
            requirements.tpm = true;
        } else if (labelWithoutLocation.equals("rktestpod")) {
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("rktest_pool")) {
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("rktest_pool2")) {
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("robo")) {
            requirements.platform = RktestYml.Platform.STATIC_ROBO;
        } else if (labelWithoutLocation.equals("robocolo")) {
            requirements.location = RktestYml.Location.COLO;
            requirements.platform = RktestYml.Platform.STATIC_ROBO;
        } else if (labelWithoutLocation.equals("robofm")) {
            requirements.roboFm = true;
        } else if (labelWithoutLocation.equals("robossd")) {
            requirements.roboSsd = true;
        } else if (labelWithoutLocation.equals("vcenter5.1")) {
            requirements.vcenter51 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("vcenter5.5")) {
            requirements.vcenter55 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("vcenter6.0")) {
            requirements.vcenter60 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("vcenter6.0_only")) {
            requirements.vcenter60 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("vcenter5.5_and_6.0")) {
            requirements.vcenter55 = true;
            requirements.vcenter60 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("vcenter6.5")) {
            requirements.vcenter65 = true;
            requirements.platform = RktestYml.Platform.DYNAPOD;
        } else if (labelWithoutLocation.equals("windows_app_test_only")) {
            requirements.windowsAppTestOnly = true;
        } else {
            LOGGER.log(
                Level.WARNING,
                "Unrecognized label (location already stripped): " +
                labelWithoutLocation +
                ". Will order an item with impossible requirements to " +
                "block the build.");
            requirements.sid =
                "impossible-sid-for-unrecognized-label-" + label;
        }
    }

    private String setDefaultLocations(Order requestedOrder) {
        String defaultLocation =
            LockableResourcesManager.get().getBodegaDefaultLocation();
        if (defaultLocation == null || defaultLocation.isEmpty()) {
            return (
                "This Jenkins instance has no default location configured, " +
                "so item locations (if any) are all exactly as specified by " +
                "the lockable resource labels.");
        }

        Gson gson = BodegaServiceUtil.getGson();
        StringBuilder itemsWithDefaultLocation = new StringBuilder();
        boolean isFirstItemWithDefaultLocation = true;
        int numItemsWithDefaultLocation = 0;
        Map<String, Object> items = requestedOrder.getItemsYaml();
        for (Map.Entry<String, Object> entry : items.entrySet()) {
            Map<String, Object> item = (Map<String, Object>) entry.getValue();
            String itemType = (String) item.get("type");
            if (itemType.equals("release_qual_baton")) {
                continue;
            }

            Map<String, Object> requirements =
                (Map<String, Object>) item.get("requirements");
            if (requirements.containsKey("location")) {
                continue;
            }

            LOGGER.finer(
                "Item \"" + entry.getKey() +
                "\" does not have a location specified, so choosing default " +
                "location \"" + defaultLocation + "\" for it.");
            requirements.put("location", defaultLocation);
            itemsWithDefaultLocation.append("\"" + entry.getKey() + "\"");
            if (isFirstItemWithDefaultLocation) {
                isFirstItemWithDefaultLocation = false;
            } else {
                itemsWithDefaultLocation.append(", ");
            }
            numItemsWithDefaultLocation++;
        }

        if (numItemsWithDefaultLocation > 0) {
            requestedOrder.setItemsYaml(items);
            return (
                "The following " + numItemsWithDefaultLocation +
                " item(s) had the Jenkins default location \"" +
                defaultLocation + "\" added to their requirements: " +
                itemsWithDefaultLocation);
        } else {
            return (
                "No items needed a default location. Their locations " +
                "(if any) are all exactly as specified by the original item " +
                "requirements or lockable resources labels.");
        }
    }

    private String setDefaultNetworks(Order requestedOrder) {
        String defaultLocation =
            LockableResourcesManager.get().getBodegaDefaultLocation();
        String availableNetworks =
            LockableResourcesManager.get().getBodegaAvailableNetworks();
        String [] networks = availableNetworks.split(",");
        Random random = new Random();
        String network = networks[random.nextInt(networks.length)].trim();

        LOGGER.finer(
            "Selected network " + network + " from available networks " +
            availableNetworks + " as the default network for Bodega orders.");
        if (availableNetworks == null || availableNetworks.isEmpty()) {
            return (
                "This Jenkins instance has no available networks configured, " +
                "so item networks (if any) are all exactly as specified by " +
                "their Bodega item requirements.");
        }

        Gson gson = BodegaServiceUtil.getGson();
        StringBuilder itemsWithDefaultNetwork = new StringBuilder();
        boolean isFirstItemWithDefaultNetwork = true;
        int numItemsWithDefaultNetwork = 0;
        Map<String, Object> items = requestedOrder.getItemsYaml();
        for (Map.Entry<String, Object> entry : items.entrySet()) {
            Map<String, Object> item = (Map<String, Object>) entry.getValue();
            String itemType = (String) item.get("type");
            if (itemType.equals("release_qual_baton")) {
                continue;
            }

            Map<String, Object> requirements =
                (Map<String, Object>) item.get("requirements");
            if (requirements.containsKey("location")) {
                String location = requirements.get("location").toString();
                if (requirements.containsKey("network")) {
                    continue;
                } else if (!location.equals(defaultLocation)) {
                    continue;
                }
            }

            LOGGER.finer(
                "Item \"" + entry.getKey() +
                "\" does not have a network specified, so choosing " +
                "network \"" + network + "\" for it.");
            requirements.put("network", network);
            itemsWithDefaultNetwork.append("\"" + entry.getKey() + "\"");
            if (isFirstItemWithDefaultNetwork) {
                isFirstItemWithDefaultNetwork = false;
            } else {
                itemsWithDefaultNetwork.append(", ");
            }
            numItemsWithDefaultNetwork++;
        }

        if (numItemsWithDefaultNetwork > 0) {
            requestedOrder.setItemsYaml(items);
            return (
                "The following " + numItemsWithDefaultNetwork +
                " item(s) had the network \"" +
                network + "\" added to their requirements: " +
                itemsWithDefaultNetwork);
        } else {
            return (
                "No items needed a network. Their networks " +
                "(if any) are all exactly as specified by the original item " +
                "requirements or lockable resources labels.");
        }
    }

    private Object getParameterValue(ParameterValue param) {
        // LabelParameterValue doesn't seem to implement getValue correctly
        // (it just returns null) so handle it specially here.
        if (param instanceof LabelParameterValue) {
            return ((LabelParameterValue) param).getLabel();
        }

        return param.getValue();
    }

    private void setParameterValue(
        Queue.Item queueItem, ParameterValue param) {

        Object desiredValue = getParameterValue(param);
        LOGGER.finer(
                "Will be trying to ensure that queue item " +
                        queueItem.getId() + " has parameter \"" +
                        param.getName() + "\" set to " + desiredValue);


        List<ParameterValue> newParamList = new ArrayList<ParameterValue>();
        newParamList.add(param);
        ParametersAction paramsAction =
                queueItem.getAction(ParametersAction.class);
        ParametersAction newParamsAction = null;
        if (paramsAction != null) {
            queueItem.removeActions(ParametersAction.class);
            LOGGER.finer("Updating existing Parameters list with " +
                    param.getName() + "and setting it to " + desiredValue );
            newParamsAction = paramsAction.createUpdated(newParamList);
        } else {
            LOGGER.finer("No existing Parameters found. Creating a new " +
                    "list with " + param.getName() + "and setting it to " +
                    desiredValue );
            newParamsAction = new ParametersAction(newParamList);
        }
        queueItem.addAction(newParamsAction);

    }

    private void addFulfilledItemsToRequiredVar(
        Queue.Item queueItem, LockableResourcesStruct requiredResources,
        Order fulfilledOrder) {

        if (requiredResources.requiredVar == null) {
            return;
        }

        Map<String, Object> items = fulfilledOrder.getItemsYaml();
        StringBuilder envVarBuilder = new StringBuilder();
        boolean firstItem = true;
        for (Map.Entry<String, JsonElement> fulfilledItemEntry :
             fulfilledOrder.fulfilledItemsJson.entrySet()) {
            Map<String, Object> item =
                (Map<String, Object>) items.get(fulfilledItemEntry.getKey());
            if (item == null) {
                LOGGER.log(
                    Level.WARNING,
                    "Not including fulfilled item \"" +
                    fulfilledItemEntry.getKey() +
                    "\" in required var because it's not present in the " +
                    "requested items.");
                continue;
            }

            String itemType = (String) item.get("type");
            if (!(itemType.equals("rktest_yml") ||
                  itemType.equals("release_qual_baton"))) {
                LOGGER.finer(
                    "Not including fulfilled item \"" +
                    fulfilledItemEntry.getKey() +
                    "\" in required var because its type \"" + itemType +
                    "\" is not one of the legacy types.");
                continue;
            }

            JsonObject fulfilledItem =
                fulfilledItemEntry.getValue().getAsJsonObject();
            String itemName = fulfilledItem.get("name").getAsString();

            if (firstItem) {
                firstItem = false;
            } else {
                envVarBuilder.append(",");
            }
            envVarBuilder.append(itemName);
        }
        String envVar = envVarBuilder.toString();

        setParameterValue(queueItem, new StringParameterValue(
            "BODEGA_FULFILLED_ITEMS",
            fulfilledOrder.fulfilledItemsJson.toString()));
        setParameterValue(queueItem, new StringParameterValue(
            requiredResources.requiredVar, envVarBuilder.toString()));
    }

    private void assignSlaveForFulfilledItems(
        Queue.Item queueItem, Order fulfilledOrder) {

        AbstractProject<?, ?> project = Utils.getProject(queueItem);
        String currentSlaveLabel = Utils.getDefaultSlaveLabel(project);

        String currentSlaveLabelWithoutLocation = null;
        if (currentSlaveLabel == null) {
            currentSlaveLabelWithoutLocation = "rkslave";
        } else if (!currentSlaveLabel.contains(":")) {
            currentSlaveLabelWithoutLocation = currentSlaveLabel;
        } else {
            LOGGER.fine(
                "Queue item " + queueItem.getId() + " is assigned to slave " +
                "label \"" + currentSlaveLabel + "\" which appears to " +
                "already specify a location, but will ignore and " +
                "potentially override the location based on Bodega items " +
                "to be consumed.");
            currentSlaveLabelWithoutLocation = currentSlaveLabel.split(":")[1];
        }

        String slaveLabelToUse = null;
        LOGGER.finest(
            "Looking through Bodega fulfilled items to determine a specific " +
            "location for slaves matching label \"" +
            currentSlaveLabelWithoutLocation + "\"");
        for (Map.Entry<String, JsonElement> fulfilledItemEntry :
             fulfilledOrder.fulfilledItemsJson.entrySet()) {
            JsonObject fulfilledItem =
                fulfilledItemEntry.getValue().getAsJsonObject();
            // We assume that any fulfilled item which does not have a
            // "location" field has no requirements/preferences for slave
            // location. This is reasonable but not necessarily guaranteed
            // since we don't know what fields on different item types may be
            // relevant.
            if (!fulfilledItem.has("location")) {
                continue;
            }

            String location = fulfilledItem.get("location").getAsString();
            // Slight hack to tolerate API change where _ in front of location
            // became optional/deprecated.
            if (location.charAt(0) != '_') {
                location = "_" + location;
            }
            String slaveLabelForItem =
                location +
                ":" + currentSlaveLabelWithoutLocation;
            if (slaveLabelToUse != null &&
                !slaveLabelToUse.equals(slaveLabelForItem)) {
                LOGGER.fine(
                    "Queue item " + queueItem.getId() +
                    " is already supposed to use slave label \"" +
                    slaveLabelToUse +
                    "\" due to a another fulfilled item, so will not " +
                    "change it to use \"" + slaveLabelForItem + "\" based " +
                    "on this fulfilled item.");
                continue;
            }

            slaveLabelToUse = slaveLabelForItem;
        }

        if (fulfilledOrder.fulfilledItemsJson.has("_jenkins_node")) {
            BodegaOrderAction bodegaOrderAction =
                queueItem.getAction(BodegaOrderAction.class);
            Gson gson = BodegaServiceUtil.getGson();
            String username = null;
            String password = null;
            String nodeName = null;
            String ipAddress = null;
            if (fulfilledOrder.fulfilledItemsJson
                              .getAsJsonObject("_jenkins_node")
                              .get("item_type")
                              .getAsString()
                              .equals("sd_dev_machine")
            ) {
                SdDevMachine sdDevMachine =
                  gson.fromJson(
                    fulfilledOrder.fulfilledItemsJson
                                  .getAsJsonObject("_jenkins_node"),
                    SdDevMachine.class);
                nodeName = sdDevMachine.name;
                username = sdDevMachine.username;
                password = sdDevMachine.password;
                ipAddress = sdDevMachine.ipAddress;
            } else if (fulfilledOrder.fulfilledItemsJson
                                     .getAsJsonObject("_jenkins_node")
                                     .get("item_type")
                                     .getAsString()
                                     .equals("cockroachdb_deps_machine")
            ) {
                CockroachDBDepsMachine crdbMachine =
                  gson.fromJson(
                    fulfilledOrder.fulfilledItemsJson
                                  .getAsJsonObject("_jenkins_node"),
                    CockroachDBDepsMachine.class);
                  nodeName = crdbMachine.name;
                  username = crdbMachine.username;
                  password = crdbMachine.password;
                  ipAddress = crdbMachine.ipv4;
            }
            try {
                Jenkins jenkins = Jenkins.getInstance();
                Node node = jenkins.getNode(nodeName);
                bodegaOrderAction.jenkinsNodeName = nodeName;
                if (node == null) {
                    // This node hasn't been added to Jenkins yet so add it
                    // now. We shouldn't attempt .addNode() multiple times
                    // since it's effectively a .put()
                    ComputerConnector connector = new SSHConnector(
                        22 /* port */,
                        username /* username */,
                        password /* password */,
                        null /* privateKey */,
                        null /* jvmOptions */,
                        null /* javaPath */,
                        null /* prefixStartSlaveCmd */,
                        null /* suffixStartSlaveCmd */);
                    ComputerLauncher launcher = connector.launch(
                        ipAddress, null);
                    EnvInjectNodeProperty envInjectNodeProperty =
                        new EnvInjectNodeProperty(
                            true /* unsetSystemVariables */,
                            null /* propertiesFilePath */);
                    List<NodeProperty<Node>> nodeProperties =
                        new ArrayList<NodeProperty<Node>>();
                    String slaveLabel =
                        LockableResourcesManager.bodegaSlaveLabel;
                    DumbSlave slave = new DumbSlave(
                        nodeName /* name */,
                        ipAddress /* nodeDescription */,
                        "." /* remoteFS */,
                        "1" /* numExecutors */,
                        Node.Mode.EXCLUSIVE /* mode */,
                        slaveLabel /* labelString */,
                        launcher /* computerLauncher */,
                        RetentionStrategy.NOOP /* retentionStrategy */,
                        nodeProperties /* nodeProperties */);
                    jenkins.addNode(slave);  // do not re-attempt, see above
                    LOGGER.fine("Adding node " + nodeName + " to Jenkins");
                } else if (node.toComputer() != null) {
                    // This node has already been added, so call .connect() in
                    // case the initial connection failed. Passing in
                    // forceReconnect=false should make this a no-op if connect
                    // activity is in-progress or complete
                    node.toComputer().connect(false);
                    LOGGER.fine("Calling .connect() for " + nodeName);
                } else {
                    // This case seems to be a non-issue - tabling for later
                    LOGGER.fine(
                        "Found node " + nodeName + " with no computer. " +
                        "This is probably bad!");
                }
            } catch (Exception e) {
                LOGGER.log(Level.WARNING, "Failed to create new slave.", e);
            }

            slaveLabelToUse = bodegaOrderAction.jenkinsNodeName;
        }

        if (slaveLabelToUse == null) {
            LOGGER.fine(
                "Didn't find any fulfilled item prescribing a slave " +
                "location for queue item " + queueItem.getId() +
                " so leaving its slave label as \"" + currentSlaveLabel +
                "\"");
        } else {
            LOGGER.fine(
                "Queue item " + queueItem.getId() +
                " will be consuming items that require slave label \"" +
                slaveLabelToUse +
                "\" so replacing its existing slave label \"" +
                currentSlaveLabel + "\"");
            LabelParameterValue slaveLabelParam =
                new LabelParameterValue("SLAVE_LABEL", slaveLabelToUse);
            slaveLabelParam.setLabel(slaveLabelToUse);
            setParameterValue(queueItem, slaveLabelParam);
        }
    }

    private void addBodegaOrderUrlAsParameter(
        Queue.Item queueItem, String bodegaOrderUrl) {

        LOGGER.log(Level.FINE,
                      "Adding environment variable BODEGA_ORDER_URL_HACK with" +
                      " a value of \"" + bodegaOrderUrl + "\" to Queue item " +
                      queueItem.getId());

        ParameterValue param = new StringParameterValue(
            "BODEGA_ORDER_URL_HACK", bodegaOrderUrl);
        setParameterValue(queueItem, param);
    }

    public static class BecauseResourcesLocked extends CauseOfBlockage {
        private final LockableResourcesStruct rscStruct;
        public BecauseResourcesLocked(LockableResourcesStruct r) {
            this.rscStruct = r;
        }

        @Override
        public String getShortDescription() {

        if (this.rscStruct.label.isEmpty())
            return "Waiting for resources " + rscStruct.required.toString();
        else
            return "Waiting for resources with label " + rscStruct.label;
        }
    }

    public static class BecauseBodegaOrder extends CauseOfBlockage {
        public final Order order;

        public BecauseBodegaOrder(Order order) {
            this.order = order;
        }

        @Override
        public String getShortDescription() {
            if (order == null) {
                return "Waiting to place Bodega order.";
            }

            return "Waiting for Bodega order " + order.sid;
        }

    }

    public static class BecauseBodegaOrderSid extends CauseOfBlockage {
        private final String orderSid;

        public BecauseBodegaOrderSid(String orderSid) {
            this.orderSid = orderSid;
        }

        @Override
        public String getShortDescription() {
            if (orderSid == null) {
                return "Waiting to place Bodega order.";
            }

            return "Waiting for Bodega order " + orderSid;
        }
    }
}
