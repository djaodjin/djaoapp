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
        // menubar
        var menubar = $('.menubar');
        var overlay = menubar.find('.header-menubar-overlay');
        var dpdwnMenu = menubar.find('.menubar-dropdown-menu');
        var dpdwnToggle = menubar.find('.menubar-dropdown-toggle')
        var open = false;
        overlay.add(dpdwnToggle).click(function(e) {
            if($(this).closest('.menubar-dropdown-menu').length === 0 ) {
                if(open){
                    open = false;
                    dpdwnMenu.hide();
                    overlay.hide();
                }
            }
        });
        dpdwnToggle.click(function(e){
            e.preventDefault();
            var $t = $(this);
            if(!open){
                e.stopPropagation();
                $t.siblings('.menubar-dropdown-container')
                  .find('.menubar-dropdown-menu')
                  .show();
                overlay.show();
                open = true;
            }
        });
        $('[data-trnc]').each(function(){
            var $el = $(this);
            var len = parseInt($el.attr('data-trnc-len'));
            var old = $el.text();
            if(old.length > len){
                var upd = old.substr(0, len) + '&hellip;';
                $el.html(upd);
            }
            $el.removeAttr('data-trnc');
        });
    })();
});

})(jQuery);

    // no exports
}));
