package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;
import retrofit2.Call;

public class SdDevMachine {
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

    @SerializedName("version")
    public String version = null;

    @SerializedName("location")
    public Location location = null;

    @SerializedName("ip_address")
    public String ipAddress = null;

    @SerializedName("username")
    public String username = null;

    @SerializedName("password")
    public String password = null;

    @Override
    public String toString() {
        return "SdDevMachine(" +
            "sid=" + sid +
            ", url=" + url +
            ", name=" + name +
            ", heldByUrl=" + heldByUrl +
            ", version=" + version +
            ", location=" + location +
            ", ipAddress=" + ipAddress +
            ", username=" + username +
            // Not logging password as a security best practice.
            ")";
    }

    public static class PageGetter implements ListPage.Getter<SdDevMachine> {
        @Override
        public Call<ListPage<SdDevMachine>> get(
            BodegaService bodega, String pageUrl) {
            return bodega.getSdDevMachinePage(pageUrl);
        }
    }

    // No Requirements class. We want to move away from needing to write Java
    // and update the plugin for clients to specify item requirements.
}
