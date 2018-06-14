package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;
import retrofit2.Call;

public class ReleaseQualBaton {
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

    @Override
    public String toString() {
        return "ReleaseQualBaton(" +
            "sid=" + sid +
            ", url=" + url +
            ", name=" + name +
            ", heldByUrl=" + heldByUrl +
            ")";
    }

    public static class PageGetter
        implements ListPage.Getter<ReleaseQualBaton> {
        @Override
        public Call<ListPage<ReleaseQualBaton>> get(
            BodegaService bodega, String pageUrl) {
            return bodega.getReleaseQualBatonPage(pageUrl);
        }
    }

    public static class Requirements {
        @SerializedName("sid")
        public String sid = null;
    }
}
