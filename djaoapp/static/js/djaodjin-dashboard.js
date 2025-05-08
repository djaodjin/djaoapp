/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */

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


/** This function will update the sidebar with id `fullSidebarId`
    to state `opened`.

    When `opened` is not specified, the function will toggle to the opposite
    of the current state of the sidebar.
 */
function toggleSidebar(fullSidebarId, opened) {
    var fullSidebar = $(fullSidebarId);
    if( fullSidebar.length > 0 ) {
        // If the sidebar is pinned, we prevent triggering the toggle.
        var pinButton = fullSidebar.find(".sidebar-pin-toggle > .fa");
        if( pinButton.length > 0 ) {
            const beforeContent = window.getComputedStyle(
                pinButton[0], '::before').content;
            if( beforeContent === '"\uf127"' ) {
                // matches `.sidebar-pin-toggle > .fa:before` content
                return;
            }
        }

        var animatedSidebar = fullSidebar.find('.sidebar-animate');
        var openToggles = $(`[data-target="${fullSidebarId}"].sidebar-toggle`);
        if( typeof opened == 'undefined' ) {
            opened = (fullSidebar.css('display') == 'none');
        }
        if( opened ) {
            if( fullSidebar.css('display') == 'none' ) {
                // otherwise sidebar is alreday opened.
                if( animatedSidebar.length > 0 ) {
                    animatedSidebar.css('left', '-220px');
                    fullSidebar.show();
                    animatedSidebar.animate({left: 0}, function(){
                        // `style="display: block, left: 0"` is compatible
                        // with a resize of the window.
                        openToggles.children().removeClass(
                            'default').addClass('opened');
                        openToggles.prev().each(function() {
                            const targetPane = $(this).data('target');
                            const menuBlocks = $(targetPane).find(
                                ".sidebar-content>ul");
                            for( var idx = 0; idx < menuBlocks.length; ++idx ) {
                                if( $(menuBlocks[idx]).css('display') != 'none' ) {
                                    $(this).show();
                                    break;
                                }
                            }
                        });
                    });
                } else {
                    fullSidebar.show();
                    openToggles.children().removeClass(
                        'default').addClass('opened');
                    openToggles.prev().each(function() {
                            const targetPane = $(this).data('target');
                            const menuBlocks = $(targetPane).find(
                                ".sidebar-content>ul");
                            for( var idx = 0; idx < menuBlocks.length; ++idx ) {
                                if( $(menuBlocks[idx]).css('display') != 'none' ) {
                                    $(this).show();
                                    break;
                                }
                            }
                    });
                }
            }
        } else {
            var prevButton = openToggles.prev();
            const prevSidebarId = prevButton.data('target');
            toggleSidebar(prevSidebarId, false);
            togglePinSidebar(fullSidebarId, false);
            if( fullSidebar.css('display') !== 'none' ) {
                // otherwise sidebar is already closed.
                if( animatedSidebar.length > 0 ) {
                    animatedSidebar.animate({left: '-220px'}, function(){
                        // We rely on `display:none` being set in the class
                        // attribute, and `left` being the only variable set
                        // in the style attribute.
                        $(this).attr('style', '');
                        fullSidebar.hide();
                        openToggles.children().removeClass(
                            'default').removeClass('opened');
                        prevButton.hide();
                    });
                } else {
                    fullSidebar.hide();
                    openToggles.children().removeClass(
                        'default').removeClass('opened');
                    prevButton.hide();
                }
            }
        }
    }
}


/** This function will update the sidebar with id `fullSidebarId`
    to state `pinned`.

    When `pinned` is not specified, the function will toggle to the opposite
    of the current state of the sidebar.
 */
function togglePinSidebar(fullSidebarId, pinned) {
    var fullSidebar = $(fullSidebarId);
    if( fullSidebar.length > 0 ) {
        var sidebarParent = fullSidebar.parent();
        if( typeof pinned == "undefined" ) {
            // `left` can be 'auto' when we are not pinned.
            pinned = !(parseInt(sidebarParent.css('left')) >= 0);
        }
        var openToggles = $(document).find(
            `[data-target="${fullSidebarId}"].sidebar-toggle`);
        openToggles.removeClass('sidebar-toggle-default');
        if( pinned ) {
            if( fullSidebar.css('display') == 'none' ) {
                openToggles.children().removeClass('opened')
            } else {
                openToggles.children().addClass('opened')
            }
            openToggles.hide();
        } else {
            if( fullSidebar.css('display') == 'none' ) {
                openToggles.children().removeClass('opened')
            } else {
                openToggles.children().addClass('opened')
            }
            openToggles.each(function() {
                var menuBlocks = fullSidebar.find(".sidebar-content>ul");
                for( var idx = 0; idx < menuBlocks.length; ++idx ) {
                    if( $(menuBlocks[idx]).css('display') != 'none' ) {
                        $(this).show();
                        break;
                    }
                }
            });
        }
        if( pinned ) {
            sidebarParent.removeClass(
                'dashboard-pane-default').addClass('dashboard-pane-pinned');
            for( let nextPinButton of fullSidebar.next().find(
                '.sidebar-pin-toggle') ) {
                const nextSidebarId = $(nextPinButton).data('target');
                togglePinSidebar(nextSidebarId, true);
            }
        } else {
            if( fullSidebar.css('display') != 'none' ) {
                fullSidebar.css('display', fullSidebar.css('display'))
            }
            sidebarParent.removeClass(
                'dashboard-pane-default dashboard-pane-pinned');
            pinButtons = $(document).find('.sidebar-pin-toggle');
            // If we are not using jQuery 3.6+, we might not be able
            // to iterate here.
            for( let prevPinButton of pinButtons ) {
                const prevSidebarId = $(prevPinButton).data('target');
                if( prevSidebarId == fullSidebarId ) break;
                togglePinSidebar(prevSidebarId, false);
            }
        }
    }
}


$(document).ready(function(){

    $('.sidebar-toggle').click(function(evt){
        evt.preventDefault();
        var $elem = $(this);
        var fullSidebarId = $elem.data('target');
        if( !fullSidebarId ) fullSidebarId = '.dashboard-nav';
        $elem.removeClass('sidebar-toggle-default');
        toggleSidebar(fullSidebarId);
    });

    $('.sidebar-pin-toggle').click(function(evt){
        evt.preventDefault();
        var $elem = $(this);
        var fullSidebarId = $elem.data('target');
        if( !fullSidebarId ) fullSidebarId = '.dashboard-nav';
        togglePinSidebar(fullSidebarId);
    });

    $(window).resize(function(){
        $('.sidebar-toggle').children().removeClass(
            'opened').addClass('closed');
    });

});

    // attach properties to the exports object to define
    // the exported module properties.
    exports.toggleSidebar = toggleSidebar;
    exports.togglePinSidebar = togglePinSidebar;
}));
