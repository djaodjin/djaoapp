/* Copyright (c) 2018, Djaodjin Inc.
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


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
        $('.sidebar-toggle').click(function(e){
            e.preventDefault();
            var $t = $(this);
            var $icon = $t.children();
            if($icon.hasClass('closed')){
                $t.animate({left: 200}); // navbar has padding-left: 16px;
                $('.navbar-brand-container').fadeOut();
                $('.dashboard-nav').css('left', '-220px').show().animate({left: 0}, function(){
                    $icon.removeClass('closed').addClass('opened');
                });
            } else {
                $t.animate({left: 0});
                $('.navbar-brand-container').fadeIn();
                $('.dashboard-nav').animate({left: '-220px'}, function(){
                    $(this).hide();
                    $icon.removeClass('opened').addClass('closed');
                });
            }
        });

        $(window).resize(function(){
            $('.dashboard-nav, .sidebar-toggle').attr('style', '');
            $('.sidebar-toggle').children().removeClass('opened').addClass('closed');
            $('.navbar-brand-container').attr('style', '');
        });
    })();
});

})(jQuery);

    // no exports
}));
