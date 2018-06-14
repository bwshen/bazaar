"""Reference: https://docs.djangoproject.com/en/1.10/topics/http/urls/."""

import bodega_all.views
import permission
from bodega_all.item_types import item_tools
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from rest_framework.routers import DefaultRouter


permission.autodiscover()

api_router = DefaultRouter()
api_router.register(r'items', bodega_all.views.ItemViewSet)
api_router.register(r'jenkins_tasks', bodega_all.views.JenkinsTaskViewSet)
api_router.register(r'orders', bodega_all.views.OrderViewSet)
api_router.register(r'order_updates', bodega_all.views.OrderUpdateViewSet)
# Need to specify base_name for ProfileViewSet because like UserViewSet,
# it is backed by the User model, so they both end up with base_name='User'
# which seems to confuse the router.
api_router.register(r'profile', bodega_all.views.ProfileViewSet,
                    base_name='Profile')
api_router.register(r'tabs', bodega_all.views.TabViewSet)
api_router.register(r'tasks', bodega_all.views.TaskViewSet)
api_router.register(r'users', bodega_all.views.UserViewSet)
item_tools.register_routes(api_router)


urlpatterns = [
    # Examples:
    # url(r'^$', 'thesite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(api_router.urls)),
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    url(r'^auth/', include('rest_framework_social_oauth2.urls')),
]

# The playground app is not necessarily installed, since we don't want it in
# production. So, add the following routes only if it is installed, to avoid
# any import failures.
if 'playground' in settings.INSTALLED_APPS:
    from playground.views import (
        BallViewSet, DollViewSet, ProfileViewSet, StickViewSet, ToyViewSet,
        UserViewSet)

    # Create a router and register the viewsets that are in the playground app.
    playground_router = DefaultRouter()
    playground_router.register(r'balls', BallViewSet)
    playground_router.register(r'dolls', DollViewSet)
    playground_router.register(r'sticks', StickViewSet)
    playground_router.register(r'toys', ToyViewSet)
    # Need to specify base_name for ProfileViewSet because like UserViewSet,
    # it is backed by the User model, so they both end up with base_name='User'
    # which seems to confuse the router.
    playground_router.register(r'profile', ProfileViewSet, base_name='Profile')
    playground_router.register(r'users', UserViewSet)

    urlpatterns += [
        url(r'^playground/api/', include(playground_router.urls)),
        url(r'^playground/api-auth/',
            include('rest_framework.urls', namespace='rest_framework')),
    ]
