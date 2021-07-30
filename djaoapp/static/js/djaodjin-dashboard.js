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
