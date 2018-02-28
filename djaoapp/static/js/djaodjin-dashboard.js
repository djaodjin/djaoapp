/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    $(".dashboard-nav-toggle").click(function() {
        var element = $(this);
        var icon = element.children("i");
        var nav = element.parents(".dashboard-nav");
        var containerInner = nav.parents(".dashboard-inner-container");
        var navWidth = nav.width();
        var toggleWidth = element.width();
        var sidebarEdge = containerInner.css("left");
        icon.removeClass();
        if( sidebarEdge === "-" + (navWidth - toggleWidth) + "px" ) {
            sidebarEdge = 0;
            icon.addClass("fa fa-angle-double-left");
        } else {
            sidebarEdge = "-" + (navWidth - toggleWidth) + "px";
            icon.addClass("fa fa-angle-double-right");
        }
        var animates = {left: sidebarEdge};
        var container =  containerInner.parents(".dashboard-container");
        var containerW = container.width();
        if( containerW >= 768 ) {
            if( sidebarEdge ) {
                var newInnerWidth = containerW + (navWidth - toggleWidth);
                animates['width'] = "" + newInnerWidth + "px";
            } else {
                animates['width'] = "" + containerW + "px";
            }
        }
        containerInner.animate(animates, 500, function() {
            container.trigger("resize");
        });
    });
});

})(jQuery);

