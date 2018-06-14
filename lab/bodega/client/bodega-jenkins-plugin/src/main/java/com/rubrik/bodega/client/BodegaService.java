package com.rubrik.bodega.client;

import java.util.List;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;
import retrofit2.http.Url;

public interface BodegaService {
    @POST("orders/")
    Call<Order> createOrder(@Body Order order);

    @GET("orders/?status_live=True")
    Call<ListPage<Order>> getListOfLiveOrders(@Query("owner_sid") String sid);

    @GET("orders/{sid}/")
    Call<Order> getOrder(@Path("sid") String sid);

    @GET
    Call<ListPage<Order>> getOrderPage(@Url String pageUrl);

    @POST("order_updates/")
    Call<OrderUpdate> createOrderUpdate(@Body OrderUpdate orderUpdate);

    @GET("profile/")
    Call<User> getProfile();

    @GET("users/{sid}/")
    Call<User> getUser(@Path("sid") String sid);

    @GET("jenkins_tasks/{sid}/")
    Call<JenkinsTask> getJenkinsTask(@Path("sid") String sid);

    @GET("tasks/{id}/")
    Call<Task> getTask(@Path("id") String id);

    @GET("rktest_ymls/")
    Call<ListPage<RktestYml>> listRktestYmls();

    @GET
    Call<ListPage<RktestYml>> getRktestYmlPage(@Url String pageUrl);

    @GET("release_qual_batons/")
    Call<ListPage<ReleaseQualBaton>> listReleaseQualBatons();

    @GET
    Call<ListPage<ReleaseQualBaton>> getReleaseQualBatonPage(
       @Url String pageUrl);

    @GET("sd_dev_machines/")
    Call<ListPage<SdDevMachine>> listSdDevMachines();

    @GET
    Call<ListPage<SdDevMachine>> getSdDevMachinePage(@Url String pageUrl);

    @GET("cockroachdb_deps_machines/")
    Call<ListPage<CockroachDBDepsMachine>> listCockroachDBDepsMachines();

    @GET
    Call<ListPage<CockroachDBDepsMachine>>
        getCockroachDBDepsMachinePage(@Url String pageUrl);
}
