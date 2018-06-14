package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import org.joda.time.DateTime;
import retrofit2.Call;

public class RktestYml {
    public static enum Platform {
        @SerializedName("AWSPOD")
        AWSPOD,

        @SerializedName("AZUREPOD")
        AZUREPOD,

        @SerializedName("CISCO")
        CISCO,

        @SerializedName("DELL")
        DELL,

        @SerializedName("DYNAPOD")
        DYNAPOD,

        @SerializedName("DYNAPOD_ROBO")
        DYNAPOD_ROBO,

        @SerializedName("DYNAPOD_ROBO_AHV")
        DYNAPOD_ROBO_AHV,

        @SerializedName("DYNAPOD_ROBO_HYPERV")
        DYNAPOD_ROBO_HYPERV,

        @SerializedName("HPE")
        HPE,

        @SerializedName("LENOVO")
        LENOVO,

        @SerializedName("PROD_BRIK")
        PROD_BRIK,

        @SerializedName("STATIC")
        STATIC,

        @SerializedName("STATIC_ROBO")
        STATIC_ROBO
    }

    public static enum Location {
        @SerializedName("COLO")
        COLO,

        @SerializedName("HQ")
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

    @SerializedName("filename")
    public String filename = null;

    @SerializedName("description")
    public String description = null;

    @SerializedName("benchmarking")
    public Boolean benchmarking = null;

    @SerializedName("hyperv_2016")
    public Boolean hyperv2016 = null;

    @SerializedName("linux_agent")
    public Boolean linuxAgent = null;

    @SerializedName("linux_agent_all_versions")
    public Boolean linuxAgentAllVersions = null;

    @SerializedName("location")
    public Location location = null;

    @SerializedName("manufacturable")
    public Boolean manufacturable = null;

    @SerializedName("model_r6xx")
    public Boolean model_r6xx = null;

    @SerializedName("mssql")
    public Boolean msSql = null;

    @SerializedName("platform")
    public Platform platform = null;

    @SerializedName("tpm")
    public Boolean tpm = null;

    @SerializedName("vcenter_5_1")
    public Boolean vcenter51 = null;

    @SerializedName("vcenter_5_5")
    public Boolean vcenter55 = null;

    @SerializedName("vcenter_6_0")
    public Boolean vcenter60 = null;

    @SerializedName("vcenter_6_5")
    public Boolean vcenter65 = null;

    @SerializedName("windows_app_test_only")
    public Boolean windowsAppTestOnly = null;

    @Override
    public String toString() {
        return "RktestYml(" +
            "sid=" + sid +
            ", url=" + url +
            ", name=" + name +
            ", heldByUrl=" + heldByUrl +
            ", filename=" + filename +
            ", benchmarking=" + benchmarking +
            ", linuxAgent=" + linuxAgent +
            ", linuxAgentAllVersions=" + linuxAgentAllVersions +
            ", location=" + (location != null ? location.name() : "null") +
            ", manufacturable=" + manufacturable +
            ", msSql=" + msSql +
            ", platform=" + (platform != null ? platform.name() : "null") +
            ", vcenter51=" + vcenter51 +
            ", vcenter55=" + vcenter55 +
            ", vcenter60=" + vcenter60 +
            ", windowsAppTestOnly=" + windowsAppTestOnly +
            ")";
    }

    public static class PageGetter implements ListPage.Getter<RktestYml> {
        @Override
        public Call<ListPage<RktestYml>> get(
            BodegaService bodega, String pageUrl) {
            return bodega.getRktestYmlPage(pageUrl);
        }
    }

    public static class Requirements {
        @SerializedName("sid")
        public String sid = null;

        @SerializedName("benchmarking")
        public Boolean benchmarking = null;

        @SerializedName("encrypted")
        public Boolean encrypted = null;

        @SerializedName("hyperv_2016")
        public Boolean hyperv2016 = null;

        @SerializedName("linux_agent")
        public Boolean linuxAgent = null;

        @SerializedName("linux_agent_all_versions")
        public Boolean linuxAgentAllVersions = null;

        @SerializedName("location")
        public Location location = null;

        @SerializedName("manufacturable")
        public Boolean manufacturable = null;

        @SerializedName("model_r6xx")
        public Boolean model_r6xx = null;

        @SerializedName("mssql")
        public Boolean msSql = null;

        @SerializedName("platform")
        public Platform platform = null;

        @SerializedName("robofm")
        public Boolean roboFm = null;

        @SerializedName("robossd")
        public Boolean roboSsd = null;

        @SerializedName("tpm")
        public Boolean tpm = null;

        @SerializedName("vcenter_5_1")
        public Boolean vcenter51 = null;

        @SerializedName("vcenter_5_5")
        public Boolean vcenter55 = null;

        @SerializedName("vcenter_6_0")
        public Boolean vcenter60 = null;

        @SerializedName("vcenter_6_5")
        public Boolean vcenter65 = null;

        @SerializedName("windows_app_test_only")
        public Boolean windowsAppTestOnly = null;
    }
}
