/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
        $('.sidebar-toggle').click(function(e){
            e.preventDefault();
            var $t = $(this);
            var $icon = $t.children();
            var targetId = $t.data('target');
            var target = targetId ? $(targetId) : $('.dashboard-nav');
            if( target.length === 0 ) {
                target = $('.dashboard-nav');
            }
            if($icon.hasClass('closed')){
                if( target ) {
                    target.css('left', '-220px').show().animate({left: 0},
                    function(){
                        // `style="display: block, left: 0"` is compatible
                        // with a resize of the window.
                        $('.sidebar-toggle').children().removeClass(
                            'closed').addClass('opened');
                    });
                }
            } else {
                if( target ) {
                    target.animate({left: '-220px'}, function(){
                        $(this).hide();
                        $(this).attr('style', '');
                        $('.sidebar-toggle').children().removeClass(
                            'opened').addClass('closed');
                    });
                }
            }
        });

        $(window).resize(function(){
            $('.sidebar-toggle').children().removeClass(
                'opened').addClass('closed');
        });
    })();
});

})(jQuery);
