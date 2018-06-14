package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;

public class User {
    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("username")
    public String username = null;

    @SerializedName("first_name")
    public String firstName = null;

    @SerializedName("last_name")
    public String lastName = null;

    @SerializedName("email")
    public String email = null;

    @SerializedName("is_superuser")
    public Boolean isSuperuser = null;

    @Override
    public String toString() {
        return "User(" +
            "sid=" + sid +
            "username=" + username +
            "email=" + email +
            ")";
    }
}
