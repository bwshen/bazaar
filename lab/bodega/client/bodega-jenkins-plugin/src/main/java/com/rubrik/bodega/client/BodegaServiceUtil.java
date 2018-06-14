package com.rubrik.bodega.client;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonDeserializer;
import com.google.gson.JsonDeserializationContext;
import com.google.gson.JsonElement;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonSerializationContext;
import com.google.gson.JsonSerializer;

import java.lang.reflect.Type;
import java.io.IOException;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import org.joda.time.DateTime;

import okhttp3.Authenticator;
import okhttp3.Cache;
import okhttp3.CacheControl;
import okhttp3.Credentials;
import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Response;
import okhttp3.Request;
import okhttp3.Route;
import retrofit2.converter.gson.GsonConverterFactory;
import retrofit2.Call;
import retrofit2.Retrofit;

public class BodegaServiceUtil {
    private static final String CACHE_LOCATION =
         "/tmp/jenkins_bodega_client_cache";

    private static final long CACHE_SIZE = 10 * 1024 * 1024;

    private static OkHttpClient okHttpClient = null;

    // Get an instance of BodegaService.
    public static BodegaService getService(
        final String baseUrl, final String authToken,
        final int maxCacheStalenessSeconds)
        throws KeyManagementException, NoSuchAlgorithmException {

        Gson gson = getGson();

        OkHttpClient okHttpClient = getOkHttpClient(authToken);
        Retrofit retrofit = new Retrofit.Builder()
            .callFactory(new CallFactory(
                okHttpClient, maxCacheStalenessSeconds))
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build();
        BodegaService bodega = retrofit.create(BodegaService.class);
        return bodega;
    }

    // Synchronously execute a Retrofit call (assumed to be a Bodega call)
    // and return the parsed response.
    public static <T> T getResponse(Call<T> call) throws IOException {
        retrofit2.Response<T> response = call.execute();
        if (!response.isSuccessful()) {
            throw new RuntimeException(
                "Bodega call " + call.request() +
                " failed with status " + response.code() +
                " (" + response.message() + "): " +
                response.errorBody().string());
        }

        return response.body();
    }

    public static Gson getGson() {
        return new GsonBuilder()
            .registerTypeAdapter(DateTime.class, new DateTimeAdapter())
            .create();
    }

    // Given an absolute URL like
    // "https://bodega.example.com/api/orders/abcde-123456/"
    // return "/orders/abcde-123456/"
    public static String getRelativeUri(String absoluteUrl) {
        int slashIndex1 = absoluteUrl.lastIndexOf("/");
        int slashIndex2 = absoluteUrl.lastIndexOf("/", slashIndex1 - 1);
        int slashIndex3 = absoluteUrl.lastIndexOf("/", slashIndex2 - 1);
        return absoluteUrl.substring(slashIndex3);
    }

    // Given an absolute URL like
    // "https://bodega.example.com/api/orders/abcde-123456/"
    // return "orders"
    public static String getEndpointCollection(String absoluteUrl) {
        int slashIndex1 = absoluteUrl.lastIndexOf("/");
        int slashIndex2 = absoluteUrl.lastIndexOf("/", slashIndex1 - 1);
        int slashIndex3 = absoluteUrl.lastIndexOf("/", slashIndex2 - 1);
        return absoluteUrl.substring(slashIndex3 + 1, slashIndex2);
    }

    // Given an absolute URL like
    // "https://bodega.example.com/api/orders/abcde-123456/"
    // return "abcde-123456"
    public static String getEndpointId(String absoluteUrl) {
        int slashIndex1 = absoluteUrl.lastIndexOf("/");
        int slashIndex2 = absoluteUrl.lastIndexOf("/", slashIndex1 - 1);
        return absoluteUrl.substring(slashIndex2 + 1, slashIndex1);
    }

    public static BodegaObject getObject(
        BodegaService bodega, String collection, String id)
        throws IOException {

        Object obj = null;
        if (collection.equals("jenkins_tasks")) {
            obj = getResponse(bodega.getJenkinsTask(id));
        } else if (collection.equals("orders")) {
            obj = getResponse(bodega.getOrder(id));
        } else if (collection.equals("tasks")) {
            obj = getResponse(bodega.getTask(id));
        }

        if (obj != null) {
            return new BodegaObject(obj);
        } else {
            return null;
        }
    }

    // Initialize okHttpClient at most once to avoid risk of multiple
    // instances simultaneously writing to the cache and corrupting it.
    // Although this interface requires an auth token, the caller is expected
    // to use the same auth token for each call since we're only creating one
    // client.
    private synchronized static OkHttpClient getOkHttpClient(
        String authToken)
        throws KeyManagementException, NoSuchAlgorithmException {

        TrustManager[] trustAllCerts = new TrustManager[] {
            new InsecureX509TrustManager()
        };

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, trustAllCerts, new SecureRandom());

        if (okHttpClient == null) {
            okHttpClient = new OkHttpClient.Builder()
                .sslSocketFactory(sslContext.getSocketFactory())
                .hostnameVerifier(new InsecureHostnameVerifier())
                .addInterceptor(new TokenAuthInterceptor(authToken))
                .cache(new Cache(new java.io.File(CACHE_LOCATION), CACHE_SIZE))
                .build();
        }

        return okHttpClient;
    }

    // An insecure trust manager we're using since our Bodega instances don't
    // have real certificates installed.
    private static class InsecureX509TrustManager implements X509TrustManager {
        @Override
        public void checkClientTrusted(
            X509Certificate[] chain, String authType)
            throws CertificateException {
            // TODO(kt) Should at least log some warnings.
        }

        @Override
        public void checkServerTrusted(
            X509Certificate[] chain, String authType)
            throws CertificateException {
            // TODO(kt) Should at least log some warnings.
        }

        @Override
        public X509Certificate[] getAcceptedIssuers() {
            // TODO(kt) Should at least log some warnings.
            return new X509Certificate[]{};
        }
    }

    // An insecure hostname verifier we're using since our Bodega instances
    // don't have real certificates installed.
    private static class InsecureHostnameVerifier implements HostnameVerifier {
         @Override
         public boolean verify(String hostname, SSLSession session) {
            // TODO(kt) Should at least log some warnings.
             return true;
         }
    }

    // An implementation of Django REST Framwork's token auth protocol.
    private static class TokenAuthInterceptor implements Interceptor {
        String authToken = null;

        TokenAuthInterceptor(final String authToken) {
            this.authToken = authToken;
        }

        @Override public Response intercept(Interceptor.Chain chain)
            throws IOException {
            return chain.proceed(
                chain.request().newBuilder()
                    .header(
                        "Authorization",
                        "Token " + authToken)
                    .build());
        }
    }

    // A wrapper call factory which sets up a cache control header
    // before delegating to okHttpClient.newCall.
    private static class CallFactory implements okhttp3.Call.Factory {
        private OkHttpClient okHttpClient = null;

        private int maxCacheStalenessSeconds = 0;

        CallFactory(
            OkHttpClient okHttpClient, int maxCacheStalenessSeconds) {
            this.okHttpClient = okHttpClient;
            this.maxCacheStalenessSeconds = maxCacheStalenessSeconds;
        }

        @Override public okhttp3.Call newCall(Request request) {
            CacheControl cacheControl = null;
            if (maxCacheStalenessSeconds > 0) {
                cacheControl = new CacheControl.Builder()
                    .maxStale(maxCacheStalenessSeconds, TimeUnit.SECONDS).
                    build();
            } else {
                cacheControl = CacheControl.FORCE_NETWORK;
            }

            return okHttpClient.newCall(
                request.newBuilder()
                    .cacheControl(cacheControl)
                    .build());
        }
    }

    private static class DateTimeAdapter
        implements JsonSerializer<DateTime>, JsonDeserializer<DateTime> {

        @Override
        public JsonElement serialize(
            DateTime src, Type typeOfSrc, JsonSerializationContext context) {

            return new JsonPrimitive(src.toString());
        }

        @Override
        public DateTime deserialize(
            JsonElement json, Type typeOfT,
            JsonDeserializationContext context) {

            return new DateTime(json.getAsJsonPrimitive().getAsString());
        }
    }
}
