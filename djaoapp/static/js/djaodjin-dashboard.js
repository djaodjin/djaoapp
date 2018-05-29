/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    var body = $('body');
    var nav = $('.dashboard-nav');
    var overlay = $('.dashboard-overlay');
    var content = $('.dashboard-content');
    $(".dashboard-header-menu .navbar-toggle").click(function() {
        content.animate({left: '220px'})
        body.css('overflow', 'hidden')
        overlay.show()
        nav.animate({left: '0'});
    });
    overlay.add('.collapse-sidebar').click(function() {
        overlay.hide()
        body.css('overflow', 'visible')
        nav.animate({left: '-350px'})
        content.animate({left: 0})
    });
    $(window).resize(function() {
        overlay.hide()
        $(body).add(nav).add(content).removeAttr('style')
    });
});

})(jQuery);

