/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    var body = $('body');
    var nav = $('.dashboard-nav');
    var overlay = $('.dashboard-overlay')
    $(".dashboard-header-menu .navbar-toggle").click(function() {
        body.css('overflow', 'hidden')
        overlay.show()
        nav.fadeIn(100);
    });
    overlay.click(function() {
        overlay.hide()
        body.css('overflow', 'visible')
        nav.fadeOut(100);
    });
    $(window).resize(function() {
        overlay.hide()
        body.css('overflow', 'visible')
        nav.hide();
    });
});

})(jQuery);

