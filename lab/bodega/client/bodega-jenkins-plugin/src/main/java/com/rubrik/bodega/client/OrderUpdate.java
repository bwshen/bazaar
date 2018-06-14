package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;

public class OrderUpdate {
    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("order_sid")
    public String orderSid = null;

    @SerializedName("time_created")
    public DateTime timeCreated = null;

    @SerializedName("creator")
    public String creatorUrl = null;

    @SerializedName("new_status")
    public Order.Status newStatus = null;

    @SerializedName("items_delta")
    public String itemsDelta = null;

    @SerializedName("time_limit_delta")
    public String timeLimitDelta = null;

    @SerializedName("comment")
    public String comment = null;

    @Override
    public String toString() {
        return "OrderUpdate(" +
            "sid=" + sid +
            "orderSid=" + orderSid +
            ", timeCreated=" + timeCreated +
            ", newStatus=" + (newStatus != null ? newStatus.name() : "null") +
            ", comment=" + comment +
            ")";
    }
}
