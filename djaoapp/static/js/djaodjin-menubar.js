/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */

// XXX If we don't define this polyfill, bootstrap-vue does not load
// correctly on phantomjs.
// We put it here so it gets loaded before `vendor-vue.js`
if (typeof Object.assign !== 'function') {
  // Must be writable: true, enumerable: false, configurable: true
  Object.defineProperty(Object, "assign", {
    value: function assign(target, varArgs) { // .length of function is 2
      'use strict';
      if (target === null || target === undefined) {
        throw new TypeError('Cannot convert undefined or null to object');
      }

      var to = Object(target);

      for (var index = 1; index < arguments.length; index++) {
        var nextSource = arguments[index];

        if (nextSource !== null && nextSource !== undefined) {
          for (var nextKey in nextSource) {
            // Avoid bugs when hasOwnProperty is shadowed
            if (Object.prototype.hasOwnProperty.call(nextSource, nextKey)) {
              to[nextKey] = nextSource[nextKey];
            }
          }
        }
      }
      return to;
    },
    writable: true,
    configurable: true
  });
}


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
        // menubar
        var menubar = $('.menubar');
        var overlay = menubar.find('.header-menubar-overlay');
        var dpdwnMenu = menubar.find('.dropdown-menu');
        var dpdwnToggle = menubar.find('.menubar-dropdown-toggle')
        var open = false;
        overlay.add(dpdwnToggle).click(function(e) {
            if($(this).closest('.dropdown-menu').length === 0 ) {
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
                  .find('.dropdown-menu')
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
