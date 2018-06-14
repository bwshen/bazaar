package com.rubrik.bodega.client;

public class BodegaObject {
    private Object obj = null;

    public BodegaObject(Object obj) {
        this.obj = obj;
    }

    public Order getOrder() {
        if (obj instanceof Order) {
            return (Order) obj;
        } else {
            return null;
        }
    }

    public JenkinsTask getJenkinsTask() {
        if (obj instanceof JenkinsTask) {
            return (JenkinsTask) obj;
        } else {
            return null;
        }
    }

    public Task getTask() {
        if (obj instanceof Task) {
            return (Task) obj;
        } else {
            return null;
        }
    }
}
