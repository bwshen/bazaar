package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;

public class Task {
    public static enum State {
        @SerializedName("PENDING")
        PENDING,

        @SerializedName("RECEIVED")
        RECEIVED,

        @SerializedName("STARTED")
        STARTED,

        @SerializedName("SUCCESS")
        SUCCESS,

        @SerializedName("FAILURE")
        FAILURE,

        @SerializedName("REVOKED")
        REVOKED,

        @SerializedName("REJECTED")
        REJECTED,

        @SerializedName("RETRY")
        RETRY,

        @SerializedName("IGNORED")
        IGNORED
    }

    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("type")
    public String type = null;

    @SerializedName("state")
    public State state = null;

    @SerializedName("display_type")
    public String displayType = null;

    @SerializedName("summary")
    public String summary = null;

    @SerializedName("time_published")
    public DateTime timePublished = null;

    @SerializedName("time_updated")
    public DateTime timeUpdated =null;

    @SerializedName("time_ready")
    public DateTime timeReady = null;

    @SerializedName("wall_time")
    public String wallTime = null;

    @SerializedName("root")
    public String rootUrl = null;

    @SerializedName("parent")
    public String parentUrl = null;

    @SerializedName("children")
    public String childrenUrl = null;

    @SerializedName("group_id")
    public String groupId = null;

    @SerializedName("origin")
    public String origin = null;
}
