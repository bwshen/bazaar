package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;

public class JenkinsTask {
    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("uuid")
    public String uuid = null;

    @SerializedName("cached_build")
    public String cachedBuildUrl = null;
}
