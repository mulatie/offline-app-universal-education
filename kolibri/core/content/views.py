from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import mimetypes
import os

from django.http import Http404
from django.http import HttpResponseRedirect
from django.http.response import FileResponse
from django.views.generic.base import View

from .models import ContentNode
from .utils.paths import get_content_storage_file_path
from kolibri.core.content.hooks import ContentNodeDisplayHook

logger = logging.getLogger(__name__)


class DownloadContentView(View):
    def get(self, request, filename, new_filename):
        """
        Handles GET requests and serves a static file as an attachment.
        """

        # calculate the local file path of the file
        path = get_content_storage_file_path(filename)

        # if the file does not exist on disk, return a 404
        if not os.path.exists(path):
            raise Http404(
                '"%(filename)s" does not exist locally' % {"filename": filename}
            )

        # generate a file response
        response = FileResponse(open(path, "rb"))

        # set the content-type by guessing from the filename
        response["Content-Type"] = mimetypes.guess_type(filename)[0]

        # set the content-disposition as attachment to force download
        response["Content-Disposition"] = "attachment;"

        # set the content-length to the file size
        response["Content-Length"] = os.path.getsize(path)

        return response


def get_by_node_id(node_id):
    """
    Function to return a content node based on a node id
    """
    if node_id:
        try:
            return ContentNode.objects.get(id=node_id)
        except (ContentNode.DoesNotExist, ValueError):
            # not found, or the id is invalid
            pass


def get_by_channel_id_and_content_id(channel_id, content_id):
    """
    Function to return a content node based on a channel_id and content_id
    """
    if channel_id and content_id:
        try:
            return ContentNode.objects.filter(
                channel_id=channel_id, content_id=content_id
            ).first()
        except ValueError:
            # Raised if a malformed UUID is passed
            pass


def get_by_content_id(content_id):
    """
    Function to return a content node based on a content_id
    """
    if content_id:
        try:
            return ContentNode.objects.filter(content_id=content_id).first()
        except ValueError:
            # Raised if a malformed UUID is passed
            pass


class ContentPermalinkRedirect(View):
    def get(self, request, *args, **kwargs):

        # extract the GET parameters
        channel_id = request.GET.get("channel_id")
        node_id = request.GET.get("node_id")
        content_id = request.GET.get("content_id")

        # first, try to get the node by the unique node_id
        node = get_by_node_id(node_id)

        # fall back to looking for the content_id in the channel if None
        node = node or get_by_channel_id_and_content_id(channel_id, content_id)

        # if it's still not found, see if we can find anything with the content_id across any channel
        node = node or get_by_content_id(content_id)

        # build up the target topic/content page URL
        if node:
            url = None
            for hook in ContentNodeDisplayHook.registered_hooks:
                url = hook.node_url(node)
            if url:
                return HttpResponseRedirect(url)

        raise Http404
