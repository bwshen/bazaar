package org.jenkins.plugins.lockableresources.queue;

import com.rubrik.bodega.client.BodegaService;
import com.rubrik.bodega.client.BodegaServiceUtil;
import com.rubrik.bodega.client.Order;
import com.rubrik.bodega.client.OrderUpdate;

import hudson.Extension;
import hudson.model.Queue;
import hudson.model.queue.QueueListener;

import java.util.logging.Level;
import java.util.logging.Logger;

import org.jenkins.plugins.lockableresources.actions.BodegaOrderAction;
import org.jenkins.plugins.lockableresources.LockableResourcesManager;

@Extension
public class BodegaQueueListener extends QueueListener {
    static final Logger LOGGER =
        Logger.getLogger(BodegaQueueListener.class.getName());

    @Override
    public void onLeft(Queue.LeftItem li) {
        if (li.isCancelled()) {
            onCancelled(li);
        }
    }

    private void onCancelled(Queue.LeftItem li) {
        BodegaOrderAction bodegaOrderAction =
            li.getAction(BodegaOrderAction.class);
        if (bodegaOrderAction == null) {
            return;
        }

        BodegaService bodega =
            LockableResourcesManager.get().getBodegaService();
        try {
            LOGGER.log(
                Level.INFO,
                "Queue item " + li + " has been cancelled, so closing its " +
                "Bodega order " + bodegaOrderAction.orderSid);
            OrderUpdate update = new OrderUpdate();
            update.orderSid = bodegaOrderAction.orderSid;
            update.newStatus = Order.Status.CLOSED;
            update.comment =
                "Was for cancelled Jenkins queue item " +
                Utils.getQueueItemDescription(li);
            OrderUpdate confirmedUpdate = BodegaServiceUtil.getResponse(
                bodega.createOrderUpdate(update));
        } catch (Exception e) {
            LOGGER.log(
                Level.WARNING,
                "Failed to close Bodega order for cancelled queue item " + li,
                e);
        }
    }
}
