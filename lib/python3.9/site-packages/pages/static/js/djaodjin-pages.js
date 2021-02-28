/**
   Functionality related to theme pages.

   These are based on jquery.
 */

/*global location setTimeout jQuery*/
/*global getMetaCSRFToken showMessages*/


(function ($) {
    "use strict";

    jQuery(document).ready(function($) {

        if( djaodjinSettings.urls.pages &&
            djaodjinSettings.urls.pages.api_themes ){

            $("#theme-upload").djupload({
                uploadUrl: djaodjinSettings.urls.pages.api_themes,
            });

            $("#reset-theme").click(function(event) {
                $.ajax({
                    method: "DELETE",
                    url: djaodjinSettings.urls.pages.api_themes,
                    datatype: "json",
                    contentType: "application/json; charset=utf-8",
                    success: function(resp) {
                        showMessages([gettext("reset to default theme")], "success");
                    },
                    error: function(resp) {
                        showErrorMessages(resp);
                    }
                });
            });
        }
    });

})(jQuery);
