package org.jenkins.plugins.lockableresources.actions;

import com.rubrik.bodega.client.BodegaService;
import com.rubrik.bodega.client.BodegaServiceUtil;
import com.rubrik.bodega.client.Order;
import com.rubrik.bodega.client.User;
import hudson.model.Action;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.jenkins.plugins.lockableresources.LockableResourcesManager;

public class BodegaOrderAction implements Action {
    static final Logger LOGGER = Logger.getLogger(
        BodegaOrderAction.class.getName());

    // We intentionally store only the order SID, not the order object itself
    // or any other state. This avoids Jenkins persisting other state which is
    // only going to become stale.
    public final String orderSid;

    // The name of the Jenkins node, if any, that was added from this order.
    // Tracked so that we know to delete it.
    public String jenkinsNodeName = null;

    /* Used to track order request time from the client side */
    private final long orderRequestTime;

    public BodegaOrderAction(String orderSid, long orderRequestTime) {
        this.orderSid = orderSid;
        this.orderRequestTime = orderRequestTime;
    }

    @Override
    public String getDisplayName() {
        // Display name for the action in the left pane of the Jenkins build.
        return "Bodega Order";
    }

    @Override
    public String getUrlName() {
        // URL the display name above links to.
        return "bodega-order";
    }

    @Override
    public String getIconFileName() {
        // Icon next to the link above.
        return "/plugin/lockable-resources/img/rubrik.jpg";
    }

    public long getOrderRequestTime() {
        return orderRequestTime;
    }

    public Order getOrder() {
        BodegaService bodega =
            LockableResourcesManager.get().getBodegaService();
        try {
            Order order = BodegaServiceUtil.getResponse(
                bodega.getOrder(orderSid));
            return order;
        } catch (Exception e) {
            LOGGER.log(
                Level.WARNING,
                "Failed to get Bodega order " + orderSid,
                e);
            return null;
        }
    }

    public String getUrlDisplayName(String url) {
        BodegaService bodega =
            LockableResourcesManager.get().getBodegaService();
        try {
            String collection = BodegaServiceUtil.getEndpointCollection(url);
            String id = BodegaServiceUtil.getEndpointId(url);
            if (collection.equals("users")) {
                User user = BodegaServiceUtil.getResponse(bodega.getUser(id));
                return user.username;
            } else {
                throw new UnsupportedOperationException(
                    "Failed to get display name for URL \"" + url +
                    "\" because collection \"" + collection +
                    "\" is unrecognized.");
            }
        } catch (Exception e) {
            LOGGER.log(
                Level.WARNING,
                "Failed to get display name for URL \"" + url + "\"",
                e);
            // Fall back to a more raw but still helpful display name.
            return BodegaServiceUtil.getRelativeUri(url);
        }
    }
}
