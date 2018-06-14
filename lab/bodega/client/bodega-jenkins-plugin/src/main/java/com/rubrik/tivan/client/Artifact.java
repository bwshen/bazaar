package com.rubrik.tivan.client;

import com.google.gson.annotations.SerializedName;

public class Artifact {
    @SerializedName("name")
    public String name = null;

    @SerializedName("timestamp")
    public String timestamp = null;

    @SerializedName("version")
    public String version = null;

    // Only exists on cdm_internal_tarball artifacts
    @SerializedName("sd_dev_bootstrap_hash")
    public String sdDevBootstrapHash = null;

    @Override
    public String toString() {
        return "Artifact(" +
            "name=" + name +
            ", timestamp=" + timestamp +
            ", version=" + version +
            ", sdDevBootstrapHash=" + sdDevBootstrapHash +
            ")";
    }
}
