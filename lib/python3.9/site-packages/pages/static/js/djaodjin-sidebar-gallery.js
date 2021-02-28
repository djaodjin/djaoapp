/* jshint multistr: true */
/* global Dropzone jQuery :true */

/* relies on:
    - jquery-ui.js
    - dropzone.js

Media request:

GET mediaUrl:

    - request

    - response: 200 OK
    {
        ...,
        "results":[
            {"location": "/media/item/url1.jpg", "tags" : []},
            {"location": "/media/item/url2.jpg", "tags" : ["html", "django"]}
        ],
        ...
    }

POST mediaUrl:
    - request: {<paramNameUpload>: uploaded_file}

    - response: 201 CREATED
    {"location":"/media/item/url1.jpg","tags":[]}


PUT mediaUrl:

    - request: {items: [{location: "/media/item/url1.jpg"}, {location: "/media/item/url2.jpg"}], tags: ["tag1", "tag2"]}

    - response: 200 OK
    {
        ...,
        "results":[
            {"location": "/media/item/url1.jpg", "tags" : ["tag1", "tag2"]},
            {"location": "/media/item/url2.jpg", "tags" : ["tag1", "tag2"]}
        ],
        ...
    }

DELETE mediaUrl 200 OK
    - request: {items: [{location: "/media/item/url1.jpg"}, {location: "/media/item/url2.jpg"}]}
    - response: 200 OK

Options:

    mediaUrl :                          default: null, type: String, url to get, post, put and delete media from backend

    // AWS S3 Direct upload settings
    S3DirectUploadUrl :                 default: null, type: String, A S3 url
    mediaPrefix :                       default: null, type: String, S3 folder ex: media/
    accessKey :                         default: null, type: String, S3 Temporary credentials
    securityToken :                     default: null, type: String, S3 Temporary credentials
    policy :                            default: null, type: String, S3 Temporary credentials
    signature :                         default: null, type: String, S3 Temporary credentials
    amzCredential :                     default: null, type: String, S3 Temporary credentials
    amzDate :                           default: null, type: String, S3 Temporary credentials

    // Custom gallery callback and templates
    paramNameUpload :                   default: "file", type: String, Custom param name for uploaded file
    maxFilesizeUpload :                 default: 256, type: Integer
    acceptedImages :                    default: [".jpg", ".png", ".gif"], type: Array
    acceptedVideos :                    default: [".mp4"], type: Array
    buttonClass :                       type: String
    galleryItemOptionsTemplate :        type: String, template used when a media item is selected
    selectedMediaClass :                type: String, class when a media item is selected
    startLoad :                         type: Boolean, if true load image on document ready
    itemUploadProgress :                type:function, params:progress, return the progress on upload
    galleryMessage :                    type:function, params:message, notification of the gallery

    // Custom droppable media item and callback
    mediaPlaceholder :                  type:string, seclector to init droppable placeholder
    saveDroppedMediaUrl :               type:string, Url to send request when media is dropped in placeholder
    droppedMediaCallback :              type:function, params:response, Callback on succeeded dropped media item

*/

(function ($) {
    "use strict";

    function Djgallery(el, options){
        this.element = $(el);
        this.options = options;
        this.init();
    }

    Djgallery.prototype = {
        init: function(){
            var self = this;
            self.originalTags = [];
            self.currentInfo = "";
            self.selectedMedia = null;
            self.initGallery();
            self.initDocument();
            self.initMediaInfo();
            if (self.options.startLoad){
                self.loadImage();
            }
            $(document).on("click", "[data-dj-gallery-media-url]" , function(){
                this.select();
            });
        },

        initGallery: function(){
            var self = this;
            if ($(".dj-gallery").length === 0){
                $("body").append(self.options.galleryTemplate);
            }
        },

        initDocument: function(){
            var self = this;
            self.element.on("click", ".dj-gallery-delete-item",
                function(event) { self.deleteMedia(event); });
            self.element.on("click", ".dj-gallery-preview-item",
                function(event) { self.previewMedia(event); });
            self.element.on("keyup", ".dj-gallery-filter",
                function(event) { self.loadImage(); });
            self.element.on("click", ".dj-gallery-tag-item",
                function(event) { self.tagMedia(); });
            self.element.on("click", ".dj-gallery-item-container",
                function(event) { self.selectMedia($(this)); });
            self.element.on("djgallery.loadresources",
                function(event) { self.loadImage(); });
            $(".dj-gallery-load").on("click",
                function(event) { self.loadImage(); });

            $("body").on("click", ".closeModal", function(event){
                event.preventDefault();
                $("#openModal").remove();
            });

            $(self.options.mediaPlaceholder).droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    var location = self._mediaLocation(
                        ui.draggable.attr("src"));
                    var source = location.toLowerCase();
                    if (droppable.prop("tagName") === "IMG"){
                        if (self.options.acceptedImages.some(function(v) {
                            return source.indexOf(v) >= 0; })) {
                            droppable.attr("src", location);
                            $(ui.helper).remove();
                            self.saveDroppedMedia(droppable);
                        }else{
                            self.options.galleryMessage(interpolate(gettext("This placeholder accepts only: %s files."),
                                [self.options.acceptedImages.join(", ")]));
                        }
                    }else if (droppable.prop("tagName") === "VIDEO"){
                        if (self.options.acceptedVideos.some(function(v) {
                            return source.indexOf(v) >= 0; })){
                            droppable.attr("src", location);
                            $(ui.helper).remove();
                            self.saveDroppedMedia(droppable);
                        }else{
                            self.options.galleryMessage(interpolate(gettext("This placeholder accepts only: %s files."),
                                [self.options.acceptedVideos.join(", ")]));
                        }
                    }
                }
            });
        },

        _mediaLocation: function(url) {
            var parser = document.createElement('a');
            parser.href = url;
            var result = parser.pathname;
            if( parser.host != location.hostname ) {
                result = parser.host + result;
                if( parser.protocol ) {
                    result = parser.protocol + "//" + result;
                }
            }
            return result;
        },

        initMediaInfo: function(){
            var self = this;
            $(".dj-gallery-info-item").text(gettext("Click on an item to view more options"));
        },

        initDropzone: function(){
            var self = this;
            var uploadUrl = self.options.mediaUrl;
            if( self.options.S3DirectUploadUrl &&
                self.options.S3DirectUploadUrl.indexOf("/api/auth/") >= 0 ) {
                uploadUrl = self.options.S3DirectUploadUrl + "?public=1";
                self.options.acl = "public-read";
            }

            self.element.djupload({
                uploadUrl: uploadUrl,
                uploadZone: "body",
                uploadClickableZone: self.options.clickableArea,
                uploadParamName: "file",

                // S3 direct upload
                accessKey: self.options.accessKey,
                mediaPrefix: self.options.mediaPrefix,
                securityToken: self.options.securityToken,
                acl: self.options.acl,
                policy: self.options.policy,
                signature: self.options.signature,
                amzCredential: self.options.amzCredential,
                amzDate: self.options.amzDate,

                // callback
                uploadSuccess: function(file, response){
                    var status = file.xhr.status;
                    $(".dz-preview").remove();
                    var lastIndex = $(".dj-gallery-items").children().last().children().attr("id");
                    if (lastIndex){
                        lastIndex = parseInt(lastIndex.split("image_")[1]) + 1;
                    }else{
                        lastIndex = 0;
                    }
                    if ([201, 204].indexOf(status) >= 0){
                        self.addMediaItem(response, lastIndex, false);
                        self.options.galleryMessage(interpolate(gettext('"%s" uploaded sucessfully to "%s"'),
                            [file.name, response.location]));
                    }else if (status === 200){
                        self.options.galleryMessage(interpolate(gettext('"%s" has previously been uploaded to "%s"'),
                            [file.name, response.location]));
                    }
                },
                uploadError: function(file, resp){
                    var message = resp;
                    if( typeof resp.detail !== "undefined" ) {
                        message = resp.detail;
                    }
                    self.options.galleryMessage(message, "error");
                },
                uploadProgress: function(file, progress){
                    self.options.itemUploadProgress(progress);
                }
            });
        },

        _loadMedias: function() {
            var self = this;
            var $element = $(self.element);
            var mediaFilterUrl = self.options.mediaUrl;
            var $filter = $element.find(".dj-gallery-filter");
            if( $filter.val() !== "") {
                mediaFilterUrl = self.options.mediaUrl + "?q=" + $filter.val();
            }
            $.ajax({
                method: "GET",
                url: mediaFilterUrl,
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(data){
                    $(".dj-gallery-items").empty();
                    $.each(data.results, function(index, file){
                        self.addMediaItem(file, index, true);
                    });
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        },

        loadImage: function(){
            var self = this;
            self.initDropzone();
            self._loadMedias();
        },

        addMediaItem: function(file, index, init){
            var self = this;
            var mediaItem = null;
            var tags = file.tags;
            if (typeof tags === "undefined"){
                tags = "";
            }
            var ext = null;
            var parser = document.createElement('a');
            parser.href = file.location;
            var filename = parser.pathname.toLowerCase();
            var extIdx = filename.lastIndexOf('.');
            if( extIdx > 0 ) {
                ext = filename.substr(extIdx);
            }
            var location = file.location;
            if( self.options.acl === "public-read" ) {
                location = self._mediaLocation(location);
            }
            if (self.options.acceptedVideos.some(function(v) { return ext.toLowerCase().indexOf(v) >= 0; })){
                mediaItem = "<video id=\"image_" + index + "\" class=\"image dj-gallery-item image_media img-thumbnail\" src=\"" + location + "\" tags=\"" + tags + "\"></video>";
            } else if (self.options.acceptedImages.some(function(v) { return ext.toLowerCase().indexOf(v) >= 0; })){
                mediaItem = "<img id=\"image_" + index + "\" class=\"image dj-gallery-item image_media img-thumbnail\" src=\"" + location + "\" tags=\"" + tags + "\">";
            } else {
                mediaItem = "<img id=\"image_" + index + "\" class=\"image dj-gallery-item image_media img-thumbnail\" src=\"/static/img/generic-document.png\" data-location=\"" + location + "\" tags=\"" + tags + "\">";
            }
            if( mediaItem ) {
                var $mediaItem = $("<div class=\"dj-gallery-item-container "
                      + self.options.mediaClass + " \">"
                      + mediaItem
                      + "</div>");
                $(".dj-gallery-items").prepend($mediaItem);
                $("#image_" + index).draggable({
                    helper: "clone",
                    revert: true,
                    appendTo: "body",
                    zIndex: 1000000,
                    start: function(event, ui) {
                        ui.helper.css({
                            width: 65
                        });
                    }
                });
                if( !init ) {
                    self.selectMedia($mediaItem);
                }
            }
        },

        selectMedia: function(item) {
            var self = this;
            var $elem = self.element;
            // Removes highlights for previously selected media
            $elem.find(".dj-gallery-item-container").not(item).removeClass(
                self.options.selectedMediaClass);

            self.selectedMedia = item.children(".dj-gallery-item");
            var refElem = item.find("[tags]");
            if( refElem.length > 0 ) {
                self.orginalTags = refElem.attr("tags").split(",");
            } else {
                self.orginalTags = "";
            }
            item.addClass(self.options.selectedMediaClass);

            // populates contextual menu
            var location = null;
            refElem = item.find("[data-location]");
            if( refElem.length > 0 ) {
                location = self._mediaLocation(refElem.data("location"));
            } else {
                refElem = item.find("[src]");
                location = self._mediaLocation(refElem.attr("src"));
            }
            var icon = item.find("[src]").attr("src");
            $elem.find(".dj-gallery-info-item").html(
                self.options.galleryItemOptionsTemplate);
            $elem.find("[data-dj-gallery-media-src]").attr("src", icon);
            $elem.find("[data-dj-gallery-media-location]").attr(
                "location", location);
            $elem.find("[data-dj-gallery-media-url]").val(location);
            $elem.find("[data-dj-gallery-media-tag]").val(item.attr("tags"));
        },

        deleteMedia: function(event){
            var self = this;
            event.preventDefault();
            var location = self._mediaLocation(self.selectedMedia.attr("src"));
            $.ajax({
                method: "DELETE",
                url: self.options.mediaUrl,
                data: JSON.stringify({"items": [{"location": location}]}),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
                },
                success: function(){
                    $("[src=\"" + self.selectedMedia.attr("src") + "\"]").parent(".dj-gallery-item-container").remove();
                    $(".dj-gallery-info-item").empty();
                    self.options.galleryMessage(gettext("Media correctly deleted."));
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        },

        tagMedia: function(){
            var self = this;
            var tags = $(".dj-gallery-tag-input").val().split(",");
            for( var idx = 0; idx < tags.length; ++idx ) {
                tags[idx] = $.trim(tags[idx]);
            }
            if (tags !== self.originalTags){
                $.ajax({
                    type: "PUT",
                    url: self.options.mediaUrl,
                    data: JSON.stringify({
                        "items": [{
                            "location": self._mediaLocation(
                                self.selectedMedia.attr("src"))
                        }],
                        "tags": tags}),
                    datatype: "json",
                    contentType: "application/json; charset=utf-8",
                    beforeSend: function(xhr, settings) {
                        xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
                    },
                    success: function(response){
                        $.each(response.results, function(index, element) {
                            $("[src=\"" + element.location + "\"]").attr(
                                "tags", element.tags);
                        });
                        self.options.galleryMessage(gettext("Tags correctly updated."));
                    },
                    error: function(resp) {
                        showErrorMessages(resp);
                    }
                });
            }
        },

        elementUrl: function(idElement) {
            var self = this;
            var path = idElement;
            if( path.indexOf('/') != 0 ) path = '/' + path
            return self.options.saveDroppedMediaUrl + path;
        },

        previewMedia: function(event){
            var self = this;
            event.preventDefault();
            var src = self.selectedMedia.attr("src");
            var type = "image";
            if (self.options.acceptedVideos.some(function(v) { return src.toLowerCase().indexOf(v) >= 0; })){
                type = "video";
            }
            self.options.previewMediaItem(self.selectedMedia.attr("src"), type);
        },

        saveDroppedMedia: function(element){
            var self = this;
            var idElement = element.attr("id");
            var data = {slug: idElement, text: element.attr("src")};
            $.ajax({
                method: "PUT",
                async: false,
                url: self.elementUrl(idElement),
                data: data,
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
                },
                success: function(response){
                    self.options.droppedMediaCallback(response);
                }
            });
        }
    };

    $.fn.djgallery = function(options) {
        var opts = $.extend( {}, $.fn.djgallery.defaults, options );
        return new Djgallery($(this), opts);
    };

    $.fn.djgallery.defaults = {

        // Djaodjin gallery required options
        mediaUrl: null, // Url to get list of media and upload, update and delete a media item

        // Customize djaodjin gallery.
        buttonClass: "",
        galleryTemplate: "<div class=\"dj-gallery\">\n  <div class=\"sidebar-gallery\">\n    <h1>" + gettext('Media') + "</h1>\n    <input placeholder=\"" + gettext('Search...') + "\" class=\"dj-gallery-filter\" type=\"text\" >\n    <div class=\"dj-gallery-items\">\n    </div>\n    <div class=\"dj-gallery-info-item\"></div>\n  </div>\n</div>",
        galleryItemOptionsTemplate: "<textarea rows=\"4\" style=\"width:100%;\" readonly data-dj-gallery-media-url></textarea>\n<button data-dj-gallery-media-location class=\"dj-gallery-delete-item\">" + gettext('Delete') + "</button>\n<button data-dj-gallery-media-location class=\"dj-gallery-preview-item\">" + gettext('Preview') + "</button>\n<br>\n<input data-dj-gallery-media-tag class=\"dj-gallery-tag-input\" type=\"text\" placeholder=\"" + gettext('Please enter tag.') + "\"><button class=\"dj-gallery-tag-item\">" + gettext('Update tags') + "</button>",
        mediaClass: "",
        selectedMediaClass: "dj-gallery-active-item",
        startLoad: false,
        itemUploadProgress: function(progress){ return true; },
        galleryMessage: function(message, type){ return true; },
        previewMediaItem: function(src){ return true; },
        acceptedImages: [".jpg", ".png", ".gif"],
        acceptedVideos: [".mp4"],
        maxFilesizeUpload: 256,
        paramNameUpload: "file",
        clickableArea: false,

        // S3 direct upload
        S3DirectUploadUrl: null,
        accessKey: null,
        mediaPrefix: "",
        securityToken: null,
        acl: "private",
        policy: "",
        signature: null,
        amzCredential: null,
        amzDate: null,


        // Custom droppable media item and callback
        mediaPlaceholder: ".droppable-image",
        saveDroppedMediaUrl: null,
        droppedMediaCallback: function(reponse) { return true; }
    };

    Dropzone.autoDiscover = false;

    /** Sliding panel

        HTML requirements:

        <button data-target="#_panel_" data-default-width="300"></button>
        <div id="#_panel_"></div>
     */
    function PanelButton(el, options){
        this.element = $(el);
        this.options = options;
        this.defaultWidth = 300;
        this.init();
    }

    PanelButton.prototype = {
        init: function () {
            var self = this;
            var target = $(self.element.attr("data-target"));
            if( typeof self.options.defaultWidth !== "undefined" ) {
                self.defaultWidth = self.options.defaultWidth;
            } else {
                var defaultWidth = self.element.attr("data-default-width");
                if( defaultWidth ) {
                    self.defaultWidth = parseInt(defaultWidth);
                }
            }

            target.find(".close").click(function() {
                if( target.is(":visible")) {
                    target.hide();
                    self.element.show();
                }
            });

            self.element.click(function(event) {
                event.preventDefault();
                self.element.blur();
                if( self.element.hasClass("dragged") ){
                    self.element.removeClass("dragged");
                    return false;
                }
                if( target.hasClass("visible-gallery") ) {
                    target.css({right: -self.defaultWidth, width: self.defaultWidth}).removeClass("visible-gallery");
                    self.element.removeAttr("style").css({right: 0}).draggable("destroy");
                } else {
                    target.css({right: 0, width: self.defaultWidth}).addClass("visible-gallery");
                    self.element.css("right", self.defaultWidth);
                    self.element.draggable({
                        axis: "x",
                        cursor: "move",
                        containment: "window",
                        start: function(event, ui) {
                            self.element.addClass("dragged");
                        },
                        drag: function(event, ui) {
                            var viewWidth = $(window).width();
                            if (viewWidth - ui.position.left - $(ui.helper).outerWidth() >= self.defaultWidth){
                                target.css("right", "0px").css("width", viewWidth - ui.position.left - $(ui.helper).outerWidth());
                            } else {
                                self.element.css("left", viewWidth - self.defaultWidth - $(ui.helper).outerWidth());
                                return false;
                            }
                        },
                        stop: function(event, ui) {
                            var viewWidth = $(window).width();
                            if (viewWidth - ui.position.left - $(ui.helper).outerWidth() >= self.defaultWidth){
                                target.css("right", "0px").css("width", viewWidth - ui.position.left - $(ui.helper).outerWidth());
                            } else {
                                target.css("right", "0px").css("width", self.defaultWidth);
                            }
                            setTimeout( function(){
                                if( self.element.hasClass("dragged")){
                                    self.element.removeClass("dragged");
                                }
                            }, self.defaultWidth);
                        }
                    });
                    target.trigger("djgallery.loadresources");
                    target.find(".content").trigger("pages.loadresources");
                }
            });
        }
    };

    $.fn.panelButton = function(options) {
        var opts = $.extend( {}, $.fn.panelButton.defaults, options );
        return this.each(function() {
            if (!$.data(this, "panelButton")) {
                $.data(this, "panelButton", new PanelButton(this, opts));
            }
        });
    };

    $.fn.panelButton.defaults = {
//        defaultWidth: 300
    };

})(jQuery);
