/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2013, 6WIND S.A. All rights reserved.                 *
 *                                                                     *
 * This file is part of the Jenkins Lockable Resources Plugin and is   *
 * published under the MIT license.                                    *
 *                                                                     *
 * See the "LICENSE.txt" file for more information.                    *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
package org.jenkins.plugins.lockableresources.actions;

import com.rubrik.bodega.client.BodegaObject;
import com.rubrik.bodega.client.BodegaServiceUtil;

import hudson.Extension;
import hudson.model.Computer;
import hudson.model.labels.LabelAtom;
import hudson.model.Node;
import hudson.model.RootAction;
import hudson.model.User;
import hudson.node_monitors.ResponseTimeMonitor;
import hudson.security.AccessDeniedException2;
import hudson.security.Permission;
import hudson.security.PermissionGroup;
import hudson.security.PermissionScope;
import hudson.slaves.OfflineCause;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Logger;
import java.util.Set;

import javax.servlet.ServletException;

import jenkins.model.Jenkins;

import org.jenkins.plugins.lockableresources.LockableResource;
import org.jenkins.plugins.lockableresources.LockableResourcesManager;
import org.jenkins.plugins.lockableresources.Messages;
import org.kohsuke.stapler.StaplerRequest;
import org.kohsuke.stapler.StaplerResponse;

@Extension
public class LockableResourcesRootAction implements RootAction {

    private static final Logger LOGGER = Logger.getLogger(
        LockableResourcesRootAction.class.getName());

    public static final PermissionGroup PERMISSIONS_GROUP =
        new PermissionGroup(LockableResourcesManager.class,
                            Messages._PermissionGroup());
    public static final Permission UNLOCK = new Permission(PERMISSIONS_GROUP,
            Messages.UnlockPermission(),
            Messages._UnlockPermission_Description(), Jenkins.ADMINISTER,
            PermissionScope.JENKINS);
    public static final Permission RESERVE = new Permission(PERMISSIONS_GROUP,
            Messages.ReservePermission(),
            Messages._ReservePermission_Description(), Jenkins.ADMINISTER,
            PermissionScope.JENKINS);

    public static final String ICON =
        "/plugin/lockable-resources/img/device-24x24.png";

    private static final long bodegaSlaveCleanupThresholdMilliseconds =
        30 * 60 * 1000; // 30 minutes

    public String getIconFileName() {
        if (User.current() != null) {
            // only show if logged in
            return ICON;
        } else {
            return null;
        }
    }

    public String getUserName() {
        if (User.current() != null)
            return User.current().getFullName();
        else
            return null;
    }

    public String getDisplayName() {
        return "Lockable Resources";
    }

    public String getUrlName() {
        return "lockable-resources";
    }

    public boolean getUseBodega() {
        return LockableResourcesManager.get().getUseBodega();
    }

    public static List<LockableResource> getResources() {
        return LockableResourcesManager.get().getResourcesFromBackEnd();
    }

    public BodegaObject getBodegaObject(String absoluteUrl)
        throws IOException {

        return BodegaServiceUtil.getObject(
            LockableResourcesManager.get().getCachedBodegaService(),
            BodegaServiceUtil.getEndpointCollection(absoluteUrl),
            BodegaServiceUtil.getEndpointId(absoluteUrl));
    }

    public static void refreshBodegaObjectCache() throws IOException {
        for (LockableResource resource : getResources()) {
            String heldByUrl = resource.getHeldByUrl();
            if (heldByUrl == null) {
                continue;
            }

            BodegaServiceUtil.getObject(
                LockableResourcesManager.get().getBodegaService(),
                BodegaServiceUtil.getEndpointCollection(heldByUrl),
                BodegaServiceUtil.getEndpointId(heldByUrl));
        }
    }

    public static void cleanUpBodegaSlaves() throws IOException {
        Jenkins jenkins = Jenkins.getInstance();
        LabelAtom bodegaSlaveLabel = new LabelAtom(
            LockableResourcesManager.bodegaSlaveLabel);
        for (Node node : jenkins.getNodes()) {
            if (node.getAssignedLabels().contains(bodegaSlaveLabel)) {
                cleanUpBodegaSlave(jenkins, node);
            }
        }
    }

    private static void cleanUpBodegaSlave(Jenkins jenkins, Node node)
        throws IOException {
        LOGGER.finest(
            "Considering Bodega slave node \"" + node + "\" for cleanup.");
        Computer computer = node.toComputer();
        if (computer == null) {
            LOGGER.finest(
                "Node \"" + node + "\" has no Computer object, so we don't " +
                "know what to do with it.");
            return;
        }

        OfflineCause offlineCause = computer.getOfflineCause();
        boolean lackingConnectivity = false;
        if (offlineCause instanceof OfflineCause.LaunchFailed) {
            LOGGER.finest(
                "Node \"" + node + "\" has a LaunchFailed offline cause " +
                "which suggests a lack of connectivity: " + offlineCause);
            lackingConnectivity = true;
        } else if (offlineCause instanceof ResponseTimeMonitor.Data) {
            ResponseTimeMonitor.Data responseTimeData =
                (ResponseTimeMonitor.Data) offlineCause;
            if (responseTimeData.hasTooManyTimeouts()) {
                LOGGER.finest(
                    "Node \"" + node + "\" has a ResponseTimeMonitor.Data " +
                    "offline cause indicating too many timeouts, which " +
                    "suggests a lack of connectivity: " + responseTimeData);
                lackingConnectivity = true;
            } else {
                LOGGER.finest(
                    "Node \"" + node + "\" has a ResponseTimeMonitor.Data " +
                    "offline cause not yet indicating too many timeouts, " +
                    "so it might not be lacking connectivity: " +
                    responseTimeData);
            }
        } else {
            LOGGER.finest(
                "Node \"" + node + "\" has an unrecognized offline cause " +
                "which probably does not reflect a lack of connectivity: " +
                offlineCause);
        }

        if (!lackingConnectivity) {
            LOGGER.finest(
                "Node \"" + node + "\" does not appear to be offline with " +
                "a cause related to lack of connectivity, so it probably " +
                "should not be cleaned up yet.");
            return;
        }

        long nowMilliseconds = System.currentTimeMillis();
        long idleStartMilliseconds = computer.getIdleStartMilliseconds();
        long idleMilliseconds = nowMilliseconds - idleStartMilliseconds;
        long idleMinutes = idleMilliseconds / (60 * 1000);
        LOGGER.finest(
            "Node \"" + node + "\" became idle or is expected to become " +
            "idle at " + idleStartMilliseconds + " ms so has been idle for " +
            idleMilliseconds + " ms (~" + idleMinutes + " minutes).");
        if (idleMilliseconds <= bodegaSlaveCleanupThresholdMilliseconds) {
            LOGGER.finest(
                "Node \"" + node + "\" has not been idle for longer than " +
                bodegaSlaveCleanupThresholdMilliseconds + " ms. It may not " +
                "be ready for cleanup yet.");
            return;
        }

        LOGGER.fine(
            "Removing node \"" + node + "\" which appears to be a Bodega " +
            "slave that has been disconnected for a while and should be " +
            "cleaned up.");
        jenkins.removeNode(node);
    }

    public int getFreeResourceAmount(String label) {
        return LockableResourcesManager.get().getFreeResourceAmount(label);
    }

    public Set<String> getAllLabels() {
        return LockableResourcesManager.get().getAllLabels();
    }

    public int getNumberOfAllLabels() {
        return LockableResourcesManager.get().getAllLabels().size();
    }

    public void doUnlock(StaplerRequest req, StaplerResponse rsp)
            throws IOException, ServletException {
        Jenkins.getInstance().checkPermission(UNLOCK);

        String name = req.getParameter("resource");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }

        List<LockableResource> resources = new ArrayList<LockableResource>();
        resources.add(r);
        LockableResourcesManager.get().unlock(resources, null);

        rsp.forwardToPreviousPage(req);
    }

    public void doReserve(StaplerRequest req, StaplerResponse rsp)
        throws IOException, ServletException {
        Jenkins.getInstance().checkPermission(RESERVE);

        String name = req.getParameter("resource");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }

        List<LockableResource> resources = new ArrayList<LockableResource>();
        resources.add(r);
        String force = req.getParameter("force");
        // Is the invocation on behalf of another user ?
        String userName = req.getParameter("onbehalfof");
        if (userName == null)
            userName = getUserName();

        if (userName != null) {
            name = userName.replaceAll("'", "");
            LockableResourcesManager.get().reserve(resources, name, force);
        }
        rsp.forwardToPreviousPage(req);
    }

    public void doExtendlease(StaplerRequest req, StaplerResponse rsp)
        throws IOException, ServletException {
        Jenkins.getInstance().checkPermission(RESERVE);

        String name = req.getParameter("resource");
        String force = req.getParameter("force");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }

        String userName = getUserName();
        if ((userName == null || !userName.equals(r.getReservedBy()))
                && !Jenkins.getInstance().hasPermission(Jenkins.ADMINISTER)) {
            throw new AccessDeniedException2(Jenkins.getAuthentication(),
                    RESERVE);
        }

        List<LockableResource> resources = new ArrayList<LockableResource>();
        resources.add(r);
        LockableResourcesManager.get().extendlease(resources, force);

        rsp.forwardToPreviousPage(req);
    }

    public void doUnreserve(StaplerRequest req, StaplerResponse rsp)
        throws IOException, ServletException {
        Jenkins.getInstance().checkPermission(RESERVE);

        String name = req.getParameter("resource");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }

        String userName = getUserName();
        // Only the current owner of the rervation OR bugfiler bot is allowed
        // to un-reserve a resource.
        if (userName != null &&
                (userName.equals(r.getReservedBy()) ||
                 userName.equals("Bugfiler Bot"))) {
            List<LockableResource> resources =
                new ArrayList<LockableResource>();
            resources.add(r);
            LockableResourcesManager.get().unreserve(resources);
            rsp.forwardToPreviousPage(req);
        } else {
            throw new AccessDeniedException2(Jenkins.getAuthentication(),
                    RESERVE);
        }
    }

    public void doReset(StaplerRequest req, StaplerResponse rsp)
        throws IOException, ServletException {
        Jenkins.getInstance().checkPermission(UNLOCK);

        String name = req.getParameter("resource");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }

        List<LockableResource> resources = new ArrayList<LockableResource>();
        resources.add(r);
        LockableResourcesManager.get().reset(resources);

        rsp.forwardToPreviousPage(req);
    }

    /*
     * HTTP request end point for changing the Quarantine Status flag of a
     * given resource. Currently not exposed in any GUI but can be invoked with
     * a URL like
     * http://jenkins/lockable-resources/quarantine?resource=R1&statusflag=true
     *
     * */
    public void doQuarantine(StaplerRequest req, StaplerResponse rsp)
        throws IOException, ServletException {

        String name = req.getParameter("resource");
        LockableResource r = LockableResourcesManager.get().fromName(name);
        if (r == null) {
            rsp.sendError(404, "Resource not found " + name);
            return;
        }
        boolean newStatus =
            req.getParameter("statusflag").equalsIgnoreCase("true");
        List<LockableResource> resources = new ArrayList<LockableResource>();
        resources.add(r);
        LockableResourcesManager.get().setQuarantineStatus(resources,
                                                           newStatus);
        rsp.forwardToPreviousPage(req);
    }

}
