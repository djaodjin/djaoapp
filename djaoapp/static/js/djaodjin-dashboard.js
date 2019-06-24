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
            var i = $t.find('i');
            if(i.hasClass('closed')){
                $t.animate({left: 205});
                $('.navbar-brand-container').fadeOut();
                $('.dashboard-nav').css('left', '-220px').show().animate({left: 0}, function(){
                    i.removeClass('closed').addClass('opened');
                });
            } else {
                $t.animate({left: 0});
                $('.navbar-brand-container').fadeIn();
                $('.dashboard-nav').animate({left: '-220px'}, function(){
                    $(this).hide();
                    i.removeClass('opened').addClass('closed');
                });
            }
        });

        $(window).resize(function(){
            $('.dashboard-nav, .sidebar-toggle').attr('style', '');
            $('.sidebar-toggle').find('i').removeClass('opened').addClass('closed');
            $('.navbar-brand-container').attr('style', '');
        });
    })();
});

})(jQuery);
