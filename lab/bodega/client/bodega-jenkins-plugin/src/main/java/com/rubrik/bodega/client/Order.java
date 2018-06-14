package com.rubrik.bodega.client;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.yaml.snakeyaml.constructor.SafeConstructor;
import org.yaml.snakeyaml.Yaml;
import retrofit2.Call;

public class Order {
    public static enum Status {
        @SerializedName("OPEN")
        OPEN,

        @SerializedName("FULFILLED")
        FULFILLED,

        @SerializedName("CLOSED")
        CLOSED
    }

    private transient Gson gson = BodegaServiceUtil.getGson();

    // Use SafeConstructor to avoid the load method being capable of running
    // arbitrary code.
    private transient Yaml safeYaml = new Yaml(new SafeConstructor());

    @SerializedName("sid")
    public String sid = null;

    @SerializedName("url")
    public String url = null;

    @SerializedName("status")
    public Status status = null;

    @SerializedName("items")
    public String items = null;

    @SerializedName("comment")
    public String comment = null;

    @SerializedName("fulfilled_items")
    public JsonObject fulfilledItemsJson = null;

    @SerializedName("owner")
    public User owner = null;

    @SerializedName("time_limit")
    public String timeLimit = null;

    @SerializedName("updates")
    public List<OrderUpdate> updates = null;

    @Override
    public String toString() {
        return "Order(" +
            "sid=" + sid +
            ", status=" + status.name() +
            ", items=" + items +
            ", comment=" + comment +
            ", fulfilledItemsJson=" + fulfilledItemsJson +
            ")";
    }

    public Map<String, Object> getItemsYaml() {
        return (Map<String, Object>) safeYaml.load(items);
    }

    public void setItemsYaml(Map<String, Object> itemsYaml) {
        this.items = safeYaml.dump(itemsYaml);
    }

    public Map<String, OrderItem> getItems() {
        return gson.fromJson(items, Map.class);
    }

    public <T> T getFulfilledItem(String nickname, Class<T> clazz) {
        if (this.fulfilledItemsJson == null) {
            return null;
        }
        if (!this.fulfilledItemsJson.has(nickname)) {
            return null;
        }
        return gson.fromJson(this.fulfilledItemsJson.get(nickname),clazz);
    }

    public void setItems(Map<String, OrderItem> items) {
        this.items = gson.toJson(items);
    }

    public String getPurposeUrl() {
        // Look for the most recent comment containing a line that mentions
        // ".. for ... $URL ..." and return $URL.
        Pattern pattern = Pattern.compile(
            "^(.*\\s+)?[Ff]or\\s+(.*\\s+)?(https?://\\S+)(\\s+.*)?$");
        for (int i = updates.size() - 1; i >= 0; i--) {
            OrderUpdate update = updates.get(i);
            if (update.comment == null || update.comment.isEmpty()) {
                continue;
            }

            for (String line : update.comment.split("\n")) {
                Matcher matcher = pattern.matcher(line);
                if (matcher.find()) {
                    return matcher.group(3);
                }
            }
        }

        return null;
    }

    public static class PageGetter implements ListPage.Getter<Order> {
        @Override
        public Call<ListPage<Order>> get(
                BodegaService bodega, String pageUrl) {
            return bodega.getOrderPage(pageUrl);
        }
    }
}
