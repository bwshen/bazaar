package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;

public class OrderItem {
    public static enum Type {
        @SerializedName("release_qual_baton")
        RELEASE_QUAL_BATON,

        @SerializedName("rktest_yml")
        RKTEST_YML
    }

    @SerializedName("type")
    public Type type;

    @SerializedName("requirements")
    public Object requirements;
}
