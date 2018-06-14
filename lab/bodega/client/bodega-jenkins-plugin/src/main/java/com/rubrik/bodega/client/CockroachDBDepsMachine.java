package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;
import retrofit2.Call;

public class CockroachDBDepsMachine {
    public static enum Location {
        @SerializedName("_COLO")
        COLO,

        @SerializedName("_HQ")
        HQ
    }

    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("name")
    public String name = null;

    @SerializedName("held_by")
    public String heldByUrl = null;

    @SerializedName("time_held_by_updated")
    public DateTime timeHeldByUpdated = null;

    @SerializedName("location")
    public Location location = null;

    @SerializedName("ipv4")
    public String ipv4 = null;

    @SerializedName("username")
    public String username = null;

    @SerializedName("password")
    public String password = null;

    @SerializedName("version")
    public String version = null;

    @Override
    public String toString() {
        return "CockroachDBDepsMachine(" +
            "sid=" + sid +
            ", url=" + url +
            ", name=" + name +
            ", heldByUrl=" + heldByUrl +
            ", version=" + version +
            ", location=" + location +
            ", ipv4=" + ipv4 +
            ", username=" + username +
            // Not logging password as a security best practice.
            ")";
    }

    public static class PageGetter
           implements ListPage.Getter<CockroachDBDepsMachine> {
        @Override
        public Call<ListPage<CockroachDBDepsMachine>> get(
            BodegaService bodega, String pageUrl) {
            return bodega.getCockroachDBDepsMachinePage(pageUrl);
        }
    }

    // No Requirements class. We want to move away from needing to write Java
    // and update the plugin for clients to specify item requirements.
}
