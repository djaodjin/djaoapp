/* Copyright (c) 2022, Djaodjin Inc.
   see LICENSE
*/

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports', 'jQuery'], factory);
    } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
        // CommonJS
        factory(exports, require('jQuery'));
    } else {
        // Browser true globals added to `window`.
        factory(root, root.jQuery);
        // If we want to put the exports in a namespace, use the following line
        // instead.
        // factory((root.djResources = {}), root.jQuery);
    }
}(typeof self !== 'undefined' ? self : this, function (exports, jQuery) {


(function ($){
    "use strict";

    /** DjaoApp extension of the media gallery UI Element
     */
    $.fn.djaoAppMediaGallery = function(options) {
        var opts = $.extend( {}, $.fn.djaoAppMediaGallery.defaults, options );
        return this.each(function() {
            var gallery = $(this).djgallery(opts);
        });
    };

    $.fn.djaoAppMediaGallery.defaults = {
        mediaUrl: null,
        S3DirectUploadUrl: null,
        saveDroppedMediaUrl: null,
        hints: null,
        // internationalization messages
        uploadCompleteLabel: "Upload completed",

        // overriden `Djgallery` defaults not expected to change in HTML
        loadImageEvent: "gallery-opened",
        buttonClass: "btn btn-block btn-primary",
        mediaClass: "card thumbnail-gallery",
        selectedMediaClass: "thumbnail-active",
        clickableArea: ".clickable-area",

        itemUploadProgress: function(progress) {
            $(".gallery-upload-progress").slideDown();
            progress = progress.toFixed();
            $(".progress-bar").css("width", progress + "%");
            if( progress == 100 ){
                $(".progress-bar").text(this.uploadCompleteLabel);
                setTimeout(function(){
                    $(".gallery-upload-progress").slideUp();
                    $(".progress-bar").text("").css("width", "0%");
                }, 2000);
            }
        },

        galleryMessage: function(message, type) {
            if( type == 'error' ) {
                showErrorMessages(message, type);
            } else {
                if( !type ) {
                    type = "success";
                }
                showMessages([message], type);
            }
        },

        previewMediaItem: function(src, type){
            $("#modal-preview-media .modal-body").empty();
            if( type == "video" ) {
                $("#modal-preview-media .modal-body").append("<video src=\"" + src + "\" controls style=\"max-width:100%\"></video>");
            } else {
                $("#modal-preview-media .modal-body").append("<img src=\"" + src + "\" style=\"max-width:100%\">");
            }
            $("#modal-preview-media").modal('show');
        },
    };

})(jQuery);


}));
