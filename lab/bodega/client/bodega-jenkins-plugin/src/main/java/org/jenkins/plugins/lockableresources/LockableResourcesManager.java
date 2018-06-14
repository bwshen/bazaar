/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2013, 6WIND S.A. All rights reserved.                 *
 *                                                                     *
 * This file is part of the Jenkins Lockable Resources Plugin and is   *
 * published under the MIT license.                                    *
 *                                                                     *
 * See the "LICENSE.txt" file for more information.                    *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
package org.jenkins.plugins.lockableresources;

import com.rubrik.bodega.client.BodegaService;
import com.rubrik.bodega.client.BodegaServiceUtil;
import com.rubrik.bodega.client.ListPage;
import com.rubrik.bodega.client.OrderItem;
import com.rubrik.bodega.client.ReleaseQualBaton;
import com.rubrik.bodega.client.RktestYml;

import com.timgroup.statsd.NoOpStatsDClient;
import com.timgroup.statsd.NonBlockingStatsDClient;
import com.timgroup.statsd.StatsDClient;
import com.timgroup.statsd.StatsDClientErrorHandler;
import hudson.Extension;
import hudson.model.AbstractBuild;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import java.util.regex.Matcher;
import java.util.regex.Pattern;
import jenkins.model.GlobalConfiguration;
import jenkins.model.Jenkins;
import net.sf.json.JSONException;
import net.sf.json.JSONObject;

import org.jenkins.plugins.lockableresources.actions.LockableResourcesRootAction;
import org.jenkins.plugins.lockableresources.queue.LockableResourcesStruct;
import org.kohsuke.stapler.StaplerRequest;
import java.util.*;
import org.apache.commons.io.IOUtils;


@Extension
public class LockableResourcesManager extends GlobalConfiguration {
    private static final Logger LOGGER = Logger.getLogger(
        LockableResourcesManager.class.getName());

    private static final int bodegaObjectCacheRefreshIntervalSeconds = 300;

    private static final int bodegaSlaveCleanupIntervalSeconds = 600;

    public static final String bodegaSlaveLabel = "bodega_dev_machine";

    @Deprecated
    private transient int defaultPriority;
    @Deprecated
    private transient String priorityParameterName;
    private List<LockableResource> resources = null;

    private boolean useBodega = false;
    private String bodegaBaseUrl = null;
    private String bodegaAuthToken = null;
    private String bodegaDefaultLocation = null;
    private String bodegaAvailableNetworks = null;
    private String statsdHost;
    private int statsdPort;
    private volatile StatsDClient statsDClient;

    private List<LockableResource> loadBodegaResources() {
        List<LockableResource> bodegaResources =
            new ArrayList<LockableResource>();

        try {
            BodegaService bodega = getBodegaService();
            ListPage<RktestYml> rktestYmls =
                BodegaServiceUtil.getResponse(bodega.listRktestYmls());
            for (RktestYml rktestYml :
                 rktestYmls.allResults(bodega, new RktestYml.PageGetter())) {
                LockableResource resource = new LockableResource(
                    rktestYml.filename,
                    rktestYml.description,
                    null,
                    null,
                    rktestYml.location.name(),
                    OrderItem.Type.RKTEST_YML.toString(),
                    rktestYml.url,
                    0,
                    // Indicate quarantine status so legacy RkLabJenkins code
                    // knows it shouldn't try to unreserve this resource.
                    true);
                resource.setBodegaSid(rktestYml.sid);
                resource.setHeldByUrl(rktestYml.heldByUrl);
                resource.setTimeHeldByUpdated(rktestYml.timeHeldByUpdated);
                resource.setPlatform(rktestYml.platform.toString());
                bodegaResources.add(resource);
            }

            ListPage<ReleaseQualBaton> releaseQualBatons =
                BodegaServiceUtil.getResponse(bodega.listReleaseQualBatons());
            for (ReleaseQualBaton releaseQualBaton :
                 releaseQualBatons.allResults(
                     bodega, new ReleaseQualBaton.PageGetter())) {
                LockableResource resource = new LockableResource(
                    releaseQualBaton.name,
                    "Release qualification baton used for cooperative " +
                    "throttling of release pipeline runs.",
                    null,
                    null,
                    "HQ",
                    OrderItem.Type.RELEASE_QUAL_BATON.toString(),
                    releaseQualBaton.url,
                    0,
                    // Indicate quarantine status so legacy RkLabJenkins code
                    // knows it shouldn't try to unreserve this resource.
                    true);
                resource.setBodegaSid(releaseQualBaton.sid);
                resource.setHeldByUrl(releaseQualBaton.heldByUrl);
                resource.setTimeHeldByUpdated(
                    releaseQualBaton.timeHeldByUpdated);
                bodegaResources.add(resource);
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to get Bodega resources.", e);
        }

        return bodegaResources;
    }

    private String _runProcessCaptureOutput(String[] cmdArray)
        throws IOException, InterruptedException {
        try {
            Process process = Runtime.getRuntime().exec(cmdArray, null);
            process.waitFor();
            String cmd_output = IOUtils.toString(process.getInputStream());
            return cmd_output.replaceAll("\\s+", "");
        } catch(IOException ioe) {
             ioe.printStackTrace();
        }
        return null;
    }

    private int _rkLeaseManager(String op, String rsrcName) {
        String[] cmdArray = new String[3];
        cmdArray[0] = "/var/lib/jenkins/sdmain/lab/lrm.py";
        cmdArray[1] = op;
        cmdArray[2] = rsrcName;
        try {
            String cmd_output = _runProcessCaptureOutput(cmdArray);
        } catch(Exception e) {
            return -1;
        }
        return 0;
    }

    public LockableResourcesManager() {
        resources = new ArrayList<LockableResource>();
        load();

        Executors.newScheduledThreadPool(1)
            .scheduleAtFixedRate(new Runnable() {
                @Override
                public void run() {
                    try {
                        LockableResourcesRootAction
                            .refreshBodegaObjectCache();
                    } catch (Exception e) {
                        LOGGER.log(
                            Level.WARNING,
                            "Exception while trying to refresh Bodega " +
                            "object cache.",
                            e);
                    }
                }
            },
            0, bodegaObjectCacheRefreshIntervalSeconds, TimeUnit.SECONDS);

        Executors.newScheduledThreadPool(1)
            .scheduleAtFixedRate(new Runnable() {
                @Override
                public void run() {
                    try {
                        LockableResourcesRootAction.cleanUpBodegaSlaves();
                    } catch (Exception e) {
                        LOGGER.log(
                            Level.WARNING,
                            "Exception while trying to clean up Bodega " +
                            "slaves.",
                            e);
                    }
                }
            },
            0, bodegaSlaveCleanupIntervalSeconds, TimeUnit.SECONDS);
    }

    public boolean getUseBodega() {
        return useBodega;
    }

    public String getBodegaBaseUrl() {
        return bodegaBaseUrl;
    }

    public String getBodegaAuthToken() {
        return bodegaAuthToken;
    }

    public String getBodegaDefaultLocation() {
        return bodegaDefaultLocation;
    }

    public String getBodegaAvailableNetworks() {
        return bodegaAvailableNetworks;
    }
    /*
     * This method need not be synchronised. In the worst case, we'll
     * end up creating more than one instances of statsd client up front
     * (perhaps during first few runs or after a config change);
     * but those will be garbage collected anyway
     */
    public StatsDClient getOrCreateStatsdClient() {
        if (statsDClient != null) {
            return statsDClient;
        }
        if(statsdHost != null) {
            try {
                final String jenkinsRootUrl =
                  Jenkins.getInstance().getRootUrl();
                if (jenkinsRootUrl != null) {
                    final String jenkinsHost;
                    jenkinsHost = new URL(jenkinsRootUrl).getHost();
                    String jenkinsNickname = jenkinsHost.replace('.', '_');
                    String metricPrefix = String.format(
                      "internal.monitoring.jenkins.%s",
                      jenkinsNickname);
                    StatsDClientErrorHandler loggingErrorHandler =
                      new StatsDClientErrorHandler() {
                        @Override
                        public void handle(Exception e) {
                            LOGGER.log(Level.WARNING,"Could not post stats",e);
                        }
                    };
                    statsDClient = new NonBlockingStatsDClient(
                      metricPrefix, statsdHost, statsdPort,loggingErrorHandler);
                    LOGGER.log(Level.INFO,
                      "Initialised statsd client for host {0} with prefix {1}",
                      new String[]{statsdHost,metricPrefix});
                    return statsDClient;
                }
            } catch (MalformedURLException e) {
                LOGGER.log(
                  Level.WARNING,
                  "Unexpected error. Jenkins Url malformed?!",
                  e);
            }
        }
        else {
            LOGGER.warning("Stats host not set. Will not report stats");
        }
        /*
         * Always have a non-null statsDClient
         * This helps  us to keep the API simple - there will always
         * be _some_ statsD client. Callers will not need to do null checks
         */
        statsDClient = new NoOpStatsDClient();
        return statsDClient;
    }

    public BodegaService getBodegaService() {
        try {
            return BodegaServiceUtil.getService(
                bodegaBaseUrl, bodegaAuthToken, 0);
        } catch (Exception e) {
            throw new RuntimeException(
                "Error getting Bodega service instance", e);
        }
    }

    public BodegaService getCachedBodegaService() {
        try {
            // Use a max staleness time of double the cache refresh time so
            // the vast majority of cases will be served from cache, but in
            // case the refresh is stuck for some reason we'll still get
            // reasonably current objects.
            return BodegaServiceUtil.getService(
                bodegaBaseUrl, bodegaAuthToken,
                2 * bodegaObjectCacheRefreshIntervalSeconds);
        } catch (Exception e) {
            throw new RuntimeException(
                "Error getting cached Bodega service instance", e);
        }
    }

    public List<LockableResource> getResources() {
        return resources;
    }

    public List<LockableResource> getResourcesFromBackEnd() {
        if (useBodega) {
            return loadBodegaResources();
        } else {
            return getResources();
        }
    }

    public List<LockableResource> getResourcesFromProject(String fullName) {
        List<LockableResource> matching = new ArrayList<LockableResource>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            String rName = r.getQueueItemProject();
            if (rName != null && rName.equals(fullName)) {
                matching.add(r);
            }
        }
        return matching;
    }

    public List<LockableResource> getResourcesFromBuild(AbstractBuild<?, ?> build) {
        List<LockableResource> matching = new ArrayList<LockableResource>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            AbstractBuild<?, ?> rBuild = r.getBuild();
            if (rBuild != null && rBuild == build) {
                matching.add(r);
            }
        }
        return matching;
    }

    public Boolean isValidLabel(String label)
    {
        return label.startsWith(LockableResource.GROOVY_LABEL_MARKER)
                || this.getAllLabels().contains(label);
    }

    public Set<String> getAllSiteNames()
    {
        Set<String> siteNames = new HashSet<String>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            String siteName = r.getSiteName();
            if(siteName != null && !siteName.isEmpty())
                siteNames.add(siteName);
        }
        return siteNames;
    }

    public Set<String> getAllLabels()
    {
        Set<String> labels = new HashSet<String>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            String rl = r.getLabels();
            if (rl == null || "".equals(rl))
                continue;
            labels.addAll(Arrays.asList(rl.split("\\s+")));
        }
        return labels;
    }

    public int getFreeResourceAmount(String label)
    {
        int free = 0;
        for (LockableResource r : getResourcesFromBackEnd()) {
            if (r.isLocked() || r.isQueued() || r.isReserved())
                continue;
            if (Arrays.asList(r.getLabels().split("\\s+")).contains(label))
                free += 1;
        }
        return free;
    }

    public List<LockableResource> getResourcesWithLabelAndSiteName(
            String label,
            String expectedSiteName,
            Map<String, Object> params,
            Logger log) {
        List<LockableResource> matchedResources =
            new ArrayList<LockableResource>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            String siteName = r.getSiteName();
            if(siteName != null && !siteName.isEmpty() &&
               siteName.equals(expectedSiteName) &&
               r.isValidLabel(label, params)) {
                    matchedResources.add(r);
            }
        }
        return matchedResources;
    }

    public List<LockableResource> getResourcesWithLabels(List<String> labels,
            Map<String, Object> params) {
        List<LockableResource> matchedResources =
            new ArrayList<LockableResource>();
        for (LockableResource r : getResourcesFromBackEnd()) {
            boolean matched = false;
            for (String label : labels) {
                if (!r.isValidLabel(label, params)) {
                    matched = false;
                    break;
                }
                matched = true;
            }
            if (matched) {
                matchedResources.add(r);
            }
        }
        return matchedResources;
    }

    public List<LockableResource> getResourcesWithLabel(String label,
            Map<String, Object> params) {
        List<String> labels = Arrays.asList(label);
        return getResourcesWithLabels(labels, params);
    }


    public LockableResource fromName(String resourceName) {
        if (resourceName != null) {
            for (LockableResource r : getResourcesFromBackEnd()) {
                if (resourceName.equals(r.getName()))
                    return r;
            }
        }
        return null;
    }

    public synchronized boolean queue(List<LockableResource> resources,
            long queueItemId) {
        for (LockableResource r : resources)
            if (r.isReserved() || r.isQueued(queueItemId) || r.isLocked())
                return false;
        for (LockableResource r : resources)
            r.setQueued(queueItemId);
        return true;
    }

    public synchronized List<LockableResource> queue(LockableResourcesStruct requiredResources,
                                                     long queueItemId,
                                                     String queueItemProject,
                                                     int number,  // 0 means all
                                                     Map<String, Object> params,
                                                     String siteName,
                                                     Logger log) {
        List<LockableResource> selected = new ArrayList<LockableResource>();

        if (!checkCurrentResourcesStatus(selected, queueItemProject, queueItemId, log)) {
            // The project has another buildable item waiting -> bail out
            log.log(Level.FINEST, "{0} has another build waiting resources." +
                    " Waiting for it to proceed first.",
                    new Object[]{queueItemProject});
            return null;
        }


        List<LockableResource> candidates = new ArrayList<LockableResource>();
        Map<String, List<LockableResource>> resourcesBySiteName =
            new HashMap<String, List<LockableResource>>();
        Set<String> allSiteNames = new HashSet<String>();
        int totalCandidates = 0;

        if (requiredResources.label != null &&
            requiredResources.label.isEmpty()) {
                String loc = "ANY";
                allSiteNames.add(loc);
                candidates = requiredResources.required;
                totalCandidates += candidates.size();
                resourcesBySiteName.put(loc, candidates);
        } else {
            if (siteName != null) {
                allSiteNames.add(siteName);
            } else {
                allSiteNames = this.getAllSiteNames();
            }
            for (String loci : allSiteNames) {
                candidates =
                    getResourcesWithLabelAndSiteName(requiredResources.label,
                                                     loci, params, log);
                totalCandidates += candidates.size();
                resourcesBySiteName.put(loci, candidates);
            }
        }

        // There seem to be seldom occurances of the queueing operation being
        // invoked multiple times for the same job instance.
        // just to be sure, clean up and free up any previous claims.
        for (LockableResource x : getResourcesFromBackEnd()) {
            if (x.getQueueItemProject() != null &&
                x.getQueueItemProject().equals(queueItemProject))
                x.unqueue();
        }

        for (String ilocs : allSiteNames) {
            selected = new ArrayList<LockableResource>();
            candidates =  resourcesBySiteName.get(ilocs);


            for (LockableResource rs : candidates) {
                if (number != 0 && (selected.size() >= number)) {
                    break;
                }
                if (!rs.isReserved() && !rs.isLocked() && !rs.isQueued())
                    selected.add(rs);
            }

            // if did not get wanted amount or did not get all
            int required_amount = number == 0 ? totalCandidates : number;
            if (selected.size() < required_amount) {
                log.log(Level.FINEST, "{0} found {1} resource(s) to queue." +
                    " Waiting for correct amount: {2}.",
                    new Object[]{queueItemProject, selected.size(), required_amount});
                continue;
            }
            for (LockableResource rsc : selected) {
                rsc.setQueued(queueItemId, queueItemProject);
            }
            return selected;
        }
        return null;
    }

    // Adds already selected (in previous queue round) resources to 'selected'
    // Return false if another item queued for this project -> bail out
    private boolean checkCurrentResourcesStatus(List<LockableResource> selected,
                                                String project,
                                                long taskId,
                                                Logger log) {
        for (LockableResource r : getResourcesFromBackEnd()) {
            // This project might already have something in queue
            String rProject = r.getQueueItemProject();
            if (rProject != null && rProject.equals(project)) {
                if (r.isQueuedByTask(taskId)) {
                    // this item has queued the resource earlier
                    selected.add(r);
                } else {
                    // The project has another buildable item waiting -> bail out
                    log.log(Level.FINEST, "{0} has another build " +
                        "that already queued resource {1}. Continue queueing.",
                        new Object[]{project, r});
                    return false;
                }
            }
        }
        return true;
    }

    public synchronized boolean lock(List<LockableResource> resources,
            AbstractBuild<?, ?> build) {
        for (LockableResource r : resources) {
            if (r.isReserved() || r.isLocked()) {
                return false;
            }
        }
        for (LockableResource r : resources) {
            r.unqueue();
            r.setBuild(build);
        }
        return true;
    }

    public synchronized void unlock(List<LockableResource> resources,
            AbstractBuild<?, ?> build) {
        for (LockableResource r : resources) {
            if (build == null || build == r.getBuild()) {
                r.unqueue();
                r.setBuild(null);
            }
        }
    }


    public synchronized boolean reserve(List<LockableResource> resources,
            String userName, String force) {
        List<LockableResource> unlock_us = new ArrayList<LockableResource>();
        for (LockableResource r : resources) {
            if (r.isReserved() || r.isLocked() || r.isQueued()) {
                if (force == null) {
                    return false;
                }
                if (r.isLocked() || r.isQueued()) {
                    unlock_us.add(r);
                }
            }
        }
        unlock(unlock_us, null);

        for (LockableResource r : resources) {
            r.setReservedBy(userName);
        }
        save();
        for (LockableResource r : resources) {
                        LOGGER.log(Level.FINEST, "{0} is reserving lockable " +
                        "resource {1} with a force of {2}.",
                        new Object[]{userName, r.getName(), force});
            _rkLeaseManager("--logleasestart", r.getName());
        }
        return true;
    }

    public synchronized void extendlease(List<LockableResource> resources,
                                         String force) {
        for (LockableResource r : resources) {
                        LOGGER.log(Level.FINEST, "Lease on lockable resource " +
                            "{0} is being extended with force {1}.",
                        new Object[]{r.getName(), force});
            if (force == null) {
                _rkLeaseManager("--extendlease", r.getName());
            } else {
                _rkLeaseManager("--forceextendlease", r.getName());
            }
        }
    }


    public synchronized void setQuarantineStatus(List<LockableResource> resources,
                                                 boolean newStatus) {
        for (LockableResource r : resources) {
                r.setQuarantineStatus(newStatus);
        }
    }

    public synchronized void unreserve(List<LockableResource> resources) {
        for (LockableResource r : resources) {
            /*
             * We do not want to allow any job or end-user to free up a
             * resource to go back in pool. Only the bot agents are allowed
             * to put these resources back in useable pool.
             */
            if (r.getReservedBy().equals("Bugfiler Bot") ||
                r.getReservedBy().equals("Bodega-Bot")) {
                LOGGER.log(Level.FINEST, "Bugfiler Bot has finished processing " +
                                "resource {0} so unreserve.", new Object[]{r.getName()});
                        r.unReserve();
            } else {
                // Set them reserved by Bugfiler Bot for auto-recovery jobs.

                    if (r.isReserved()) {
                        LOGGER.log(Level.FINEST, "Transferring reservation of resource " +
                                    "{0} to Bugfiler Bot which was previously reserved " +
                                    "by {1}.", new Object[]{r.getName(), r.getReservedBy()});
                    }

                        r.setReservedBy("Bugfiler Bot");
            }
        }
        save();
        for (LockableResource r : resources) {
            _rkLeaseManager("--logleaseend", r.getName());
        }
    }

    @Override
    public String getDisplayName() {
        return "External Resources";
    }

    public synchronized void reset(List<LockableResource> resources) {
        for (LockableResource r : resources) {
            r.reset();
        }
        save();
    }

    @Override
    public boolean configure(StaplerRequest req, JSONObject json)
            throws FormException {
        try {
            useBodega = json.getBoolean("useBodega");
            bodegaBaseUrl = json.getString("bodegaBaseUrl");
            bodegaAuthToken = json.getString("bodegaAuthToken");
            bodegaDefaultLocation = json.getString("bodegaDefaultLocation");
            bodegaAvailableNetworks = json.getString("bodegaAvailableNetworks");
            statsdHost = json.getString("statsdHost");
            statsdPort = json.getInt("statsdPort");
            /*
             *  Since statsdHost config has presumably changed, it
             *  is wise to re-instantiate the statsd client
             */
            getOrCreateStatsdClient();
            List<LockableResource> newResouces = req.bindJSONToList(
                    LockableResource.class, json.get("resources"));
            for (LockableResource r : newResouces) {
                LockableResource old = fromName(r.getName());
                if (old != null) {
                    r.setBuild(old.getBuild());
                    r.setQueued(r.getQueueItemId(), r.getQueueItemProject());
                }
            }
            resources = newResouces;
            save();
            return true;
        } catch (JSONException e) {
            return false;
        }
    }

    public static LockableResourcesManager get() {
        return (LockableResourcesManager) Jenkins.getInstance()
                .getDescriptorOrDie(LockableResourcesManager.class);
    }

}
