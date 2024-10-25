/* Copyright (c) 2024, Djaodjin Inc.
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


const API_URL = typeof DJAOAPP_API_BASE_URL !== 'undefined' ?
  DJAOAPP_API_BASE_URL : "/api";


async function injectUserMenubarItem() {
  try {
    const userMenubarItem = document.querySelector(
        '[data-dj-menubar-user-item]')
    if( !userMenubarItem ) return;

    var params = {
        redirect: 'manual',
        headers: {Accept: 'text/html'}
    };
    const authToken = sessionStorage.getItem('authToken');
    if( authToken ) {
        params['headers']['Authorization'] = "Bearer " + authToken;
    } else {
        params['credentials'] = 'include';
    }

    const resp = await fetch(API_URL + '/auth/tokens', params)
    if( !resp.ok ) return;

    // The assignment will replace the inner content
    // of 'userMenubarItem' by HTMLElement, despite the response
    // received (`resp.text()`) looking like it is being decorated,
    // i.e. "<html><head></head><body>{{HTMLElement}}</body></html>".
    const data = await resp.text();
    userMenubarItem.innerHTML = data;
    userMenubarItem.removeAttribute('data-dj-menubar-user-item');
    addMenubarDropdownToggle();

  } catch(error) {
    console.error(error.message);
  }
}


function addMenubarDropdownToggle() {

    var closeEvent = false;
    for( elem of document.getElementsByClassName(
        'menubar-label-dropdown-toggle') ) {
        elem.addEventListener('click', function(evt) {
            evt.preventDefault();
            var self = this;
            var dpdwnMenu = self.parentNode.querySelector(
                '.menubar-dropdown-menu')
            if( window.getComputedStyle(dpdwnMenu).display === 'none' ) {
                dpdwnMenu.style.display = "block";
                if( !closeEvent ) {
                    window.addEventListener('mouseup', function(evt) {
                        if( !self.contains(evt.target) ) {
                            dpdwnMenu.style.display = "none";
                        }
                    });
                    closeEvent = true;
                }
            } else {
                dpdwnMenu.style.display = "none";
            }
        });
    }

    for( elem of document.querySelectorAll('[data-trnc]') ) {
        var len = parseInt(elem.getAttribute('data-trnc-len'));
        var old = elem.innerHTML;
        if( old.length > len ) {
            var upd = old.substr(0, len) + '&hellip;';
            elem.innerHTML = upd;
        }
        // removing the attribute will make the element visible.
        elem.removeAttribute('data-trnc');
    }
}


if( document.readyState === "interactive" ||
    document.readyState === "complete" ) {
    injectUserMenubarItem();
    addMenubarDropdownToggle();
} else {
    document.addEventListener('DOMContentLoaded', injectUserMenubarItem);
    document.addEventListener('DOMContentLoaded', addMenubarDropdownToggle);
}

    // attach properties to the exports object to define
    // the exported module properties.
    exports.injectUserMenubarItem = injectUserMenubarItem;
    exports.addMenubarDropdownToggle = addMenubarDropdownToggle;
}));
