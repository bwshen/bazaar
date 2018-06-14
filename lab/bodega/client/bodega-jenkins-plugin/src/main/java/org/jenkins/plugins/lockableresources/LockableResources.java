/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2015, 6WIND S.A. All rights reserved.                 *
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
import com.rubrik.bodega.client.Order;
import com.rubrik.bodega.client.OrderUpdate;
import com.rubrik.bodega.client.User;

import hudson.Plugin;
import hudson.model.Api;


import jenkins.model.Jenkins;

import java.io.File;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;


import org.kohsuke.stapler.export.Exported;
import org.kohsuke.stapler.export.ExportedBean;
import org.w3c.dom.Document;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;


@ExportedBean
public class LockableResources extends Plugin {

    private static final Logger LOGGER = Logger.getLogger(
        LockableResources.class.getName());

    private static final Pattern PATTERN_TO_MATCH_JENKINS_QUEUE_ITEM =
            Pattern.compile("For Jenkins queue item (.*).pretty=True.*");

    public Api getApi() {
        return new Api(this);
    }

    @Exported
    public List<LockableResource> getResources() {
        return Collections.unmodifiableList(LockableResourcesManager.get()
            .getResourcesFromBackEnd());
    }

    public void postInitialize() {

        Set <String> staleOrders = new HashSet<String> ();
        Set <String> ordersAssignedToQueue = new HashSet<String> ();

        LOGGER.info("Post-Initializing the Lockable Resources Plugin");
        try {

            File queueFile = new File(Jenkins.getInstance().getRootDir(),
                    "queue.xml");

            if (queueFile.exists()) {
                DocumentBuilderFactory dbFactory =
                        DocumentBuilderFactory.newInstance();
                DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
                Document doc = dBuilder.parse(queueFile);
                NodeList nList = doc.getElementsByTagName("orderSid");
                for (int i = 0; i < nList.getLength(); i++) {
                    ordersAssignedToQueue.add(nList.item(i).getTextContent());
                }
            }
        } catch(Exception e){
            LOGGER.log(Level.WARNING,
                    "Failed to read the queue.xml file " +
                            "for Jenkins Instance. Skipping rest" +
                            " of the stale order processing as failsafe", e);
            return;
        }

        LOGGER.info("Orders in the Queue: " + ordersAssignedToQueue);
        BodegaService bodega =
            LockableResourcesManager.get().getBodegaService();

        try {

            User user = BodegaServiceUtil.getResponse(bodega.getProfile());

            ListPage < Order > liveOrders = BodegaServiceUtil.getResponse(
                bodega.getListOfLiveOrders(user.sid));

            LOGGER.fine("Found " + liveOrders.count + " " +
                "live orders for the Jenkins Instance");

            for (Order order:
                    liveOrders.allResults(bodega, new Order.PageGetter())) {
                if (!ordersAssignedToQueue.contains(order.sid)) {
                    staleOrders.add(order.sid);
                }

            }

            LOGGER.fine("Found " + staleOrders.size() + " stale orders.");

        } catch (Exception e) {
            LOGGER.log(Level.WARNING,
                "Failed to get list of live orders " +
                "for Jenkins Instance", e);

        }

        for (String orderSid: staleOrders) {
            try {

                Order order = BodegaServiceUtil.getResponse(
                        bodega.getOrder(orderSid));

                // Skip the order if it's closed or if it does not
                // have any order updates
                if (order.status.equals(Order.Status.CLOSED) ||
                        order.updates.size() == 0)
                    continue;

                // Skip the order if we can not determine
                // it's related to Jenkins
                if ( ! PATTERN_TO_MATCH_JENKINS_QUEUE_ITEM.matcher(
                        order.updates.get(0).comment).find())
                    continue;

                OrderUpdate update = new OrderUpdate();
                update.orderSid = orderSid;
                update.newStatus = Order.Status.CLOSED;
                update.comment = "Found live order " + orderSid +
                        " which is no longer tracked in the queue from " +
                        Jenkins.getInstance().getRootUrl() +
                        " so closing this to prevent resource wastage.";
                BodegaServiceUtil.getResponse(bodega.createOrderUpdate(update));
                LOGGER.fine("Closed the stale order " + orderSid);

            } catch (Exception e) {
                LOGGER.log(Level.WARNING,
                    "Unable to close stale order " + orderSid, e);
            }
        }
    }
}
