package com.rubrik.bodega.client;

import com.google.gson.annotations.SerializedName;
import java.io.IOException;
import java.lang.Iterable;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import retrofit2.Call;

// A generic page of REST API query results.
public class ListPage<T> {
    @SerializedName("count")
    public int count;

    @SerializedName("next")
    public String nextPageUrl;

    @SerializedName("previous")
    public String previousPageUrl;

    @SerializedName("results")
    public List<T> results;

    // A page getter implementation that needs to be provided to use the
    // allResults() iterable. It's required because the caller needs to
    // tell GSON what structure it wants to deserialize by calling a
    // BodegaService method which has that return type.
    public static interface Getter<T> {
        public Call<ListPage<T>> get(BodegaService bodega, String pageUrl);
    }

    private ListPage<T> getNextPage(
        BodegaService bodega, Getter<T> pageGetter) throws IOException {
        if (nextPageUrl == null) {
            return null;
        }

        return BodegaServiceUtil.getResponse(
            pageGetter.get(bodega, nextPageUrl));
    }

    // An iterator which goes through all the individual results, page by page.
    private class AllResultsIterator implements Iterator<T> {
        private BodegaService bodega = null;
        private Getter<T> pageGetter = null;
        private ListPage<T> currentPage = null;
        private Iterator<T> currentResultIterator = null;

        public AllResultsIterator(
            BodegaService bodega, Getter<T> pageGetter,
            ListPage<T> currentPage) {
            this.bodega = bodega;
            this.pageGetter = pageGetter;
            this.currentPage = currentPage;
            this.currentResultIterator = currentPage.results.iterator();
        }

        @Override
        public boolean hasNext() {
            return currentResultIterator.hasNext();
        }

        @Override
        public T next() {
            if (!hasNext()) {
                throw new NoSuchElementException("No more ListPage results.");
            }

            T result = currentResultIterator.next();
            if (!currentResultIterator.hasNext()) {
                try {
                    ListPage<T> nextPage =
                        currentPage.getNextPage(bodega, pageGetter);

                    if (nextPage != null) {
                        currentPage = nextPage;
                        currentResultIterator = currentPage.results.iterator();
                    }
                } catch (IOException e) {
                    throw new RuntimeException(
                        "Encountered exception while getting next page.", e);
                }
            }

            return result;
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException(
                "Removing ListPage results is unsupported.");
        }
    }

    // An iterable of all the results in all the pages.
    public Iterable<T> allResults(
        final BodegaService bodega, final Getter<T> pageGetter) {
        final ListPage<T> currentPage = this;

        return new Iterable<T>() {
            @Override
            public Iterator<T> iterator() {
                return new AllResultsIterator(bodega, pageGetter, currentPage);
            }
        };
    }
}
