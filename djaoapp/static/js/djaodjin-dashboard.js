/* Copyright (c) 2026, Djaodjin Inc.
   see LICENSE
*/

/* global document window */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports'], factory);
    } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
        // CommonJS
        factory(exports);
    } else {
        // Browser true globals added to `window`.
        factory(root);
        // If we want to put the exports in a namespace, use the following line
        // instead.
        // factory((root.djResources = {}));
    }
}(typeof self !== 'undefined' ? self : this, function (exports) {


function _showElement(elm) {
    if( elm && elm.style.display === 'none' ) {
        elm.style.display = '';
    }
}

function _hideElement(elm) {
    if( elm ) {
        elm.style.display = 'none';
    }
}

/** Changes classes of HTML Elements for the sidebar and its visible/hidden
    toggle buttons such that the sidebar is visible and the toggles reflect
    that.

    There are typically two toggles per sidebar, one in the sidebar itself,
    and one in the top menubar.
 */
function _showSidebar(fullSidebar, fullSidebarToggles) {
    // `style="display: block, left: 0"` is compatible
    // with a resize of the window.
    fullSidebar.classList.remove('sidebar-hidden');
    fullSidebar.classList.add('sidebar-opened');
    for( let toggle of fullSidebarToggles ) {
        for( const child of toggle.children ) {
            child.classList.remove('default');
            child.classList.add('opened');
        }
    }
    // If the sidebar is visible, all parent sidebars are also visible
    // and their own toggles should show parents are visible.
    for( let toggle of fullSidebarToggles ) {
        let prev = toggle.previousElementSibling;
        if( prev ) {
            const targetPane = prev.dataset.target;
            const menuBlocks = document.querySelector(
                targetPane).querySelectorAll(".sidebar-content>ul");
            for( var idx = 0; idx < menuBlocks.length; ++idx ) {
                const menuBlockStyle = window.getComputedStyle(
                    menuBlocks[idx]);
                if( menuBlockStyle.display != 'none' ) {
                    _showElement(prev);
                    break;
                }
            }
        }
    }
}


/** Changes classes of HTML Elements for the sidebar and its visible/hidden
    toggle buttons such that the sidebar is hidden and the toggles reflect
    that.

    There are typically two toggles per sidebar, one in the sidebar itself,
    and one in the top menubar.
 */
function _hideSidebar(fullSidebar, fullSidebarToggles) {
    fullSidebar.classList.remove('sidebar-opened');
    fullSidebar.classList.add('sidebar-hidden');
    for( let toggle of fullSidebarToggles ) {
        for( const child of toggle.children ) {
            child.classList.remove('default');
            child.classList.remove('opened');
        }
    }
}


/** This function will update the sidebar with id `fullSidebarId`
    to state `opened`.

    When `opened` is not specified, the function will toggle to the opposite
    of the current state of the sidebar.
 */
function toggleSidebar(fullSidebarId, toOpened) {
    var opened = toOpened;
    var fullSidebar = document.getElementById(
        ( fullSidebarId.length > 0 && fullSidebarId[0] === '#' ) ?
        fullSidebarId.slice(1) : fullSidebarId);
    if( fullSidebar ) {
        // If the sidebar is pinned, we prevent triggering the toggle.
        var pinButton = fullSidebar.querySelector(".sidebar-pin-toggle > .fa");
        if( pinButton ) {
            const beforeContent = window.getComputedStyle(
                pinButton, '::before').content;
            if( beforeContent === '"\uf127"' ) {
                // matches `.sidebar-pin-toggle > .fa:before` content
                return;
            }
        }
        var fullSidebarToggles = document.querySelectorAll(
            `[data-target="${fullSidebarId}"].sidebar-toggle`);
        const fullSidebarHidden = (
            window.getComputedStyle(fullSidebar).display === 'none');
        if( typeof opened == 'undefined' ) {
            opened = fullSidebarHidden;
        }
        if( opened ) {
            if( fullSidebarHidden ) {
                // otherwise sidebar is alreday opened.
                _showSidebar(fullSidebar, fullSidebarToggles);
            }
        } else {
            for( let toggle of fullSidebarToggles ) {
                // If we hide a sidebar, we will also hide all sidebar
                // above in the hierarchy.
                let prev = toggle.previousElementSibling;
                if( prev ) {
                    const prevSidebarId = prev.dataset.target;
                    toggleSidebar(prevSidebarId, false);
                }

                togglePinSidebar(fullSidebarId, false);
                if( !fullSidebarHidden ) {
                    // otherwise sidebar is already closed.
                    _hideSidebar(fullSidebar, fullSidebarToggles);
                    if( prev ) {
                        _hideElement(prev);
                    }
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
    var fullSidebar = document.getElementById(
        ( fullSidebarId.length > 0 && fullSidebarId[0] === '#' ) ?
        fullSidebarId.slice(1) : fullSidebarId);
    if( fullSidebar ) {
        var sidebarParent = fullSidebar.parentElement;
        if( typeof pinned == "undefined" ) {
            // `left` can be 'auto' when we are not pinned.
            const sidebarParentStyle = window.getComputedStyle(sidebarParent);
            pinned = !(parseInt(sidebarParentStyle.left) >= 0);
        }
        var fullSidebarToggles = document.querySelectorAll(
            `[data-target="${fullSidebarId}"].sidebar-toggle`);
        for( toggle of fullSidebarToggles ) {
            toggle.classList.remove('sidebar-toggle-default');
        }
        const fullSidebarStyle = window.getComputedStyle(fullSidebar);
        if( pinned ) {
            if( fullSidebarStyle.display === 'none' ) {
                for( toggle of fullSidebarToggles ) {
                    for( const child of toggle.children ) {
                        child.classList.remove('opened')
                    }
                }
            } else {
                for( toggle of fullSidebarToggles ) {
                    for( const child of toggle.children ) {
                        child.classList.add('opened')
                    }
                }
            }
            for( toggle of fullSidebarToggles ) {
                _hideElement(toggle)
            }
        } else {
            if( fullSidebarStyle.display === 'none' ) {
                for( toggle of fullSidebarToggles ) {
                    for( const child of toggle.children ) {
                        child.classList.remove('opened')
                    }
                }
            } else {
                for( toggle of fullSidebarToggles ) {
                    for( const child of toggle.children ) {
                        child.classList.add('opened')
                    }
                }
            }
            for( toggle of fullSidebarToggles ) {
                var menuBlocks = fullSidebar.querySelectorAll(
                    ".sidebar-content>ul");
                for( var idx = 0; idx < menuBlocks.length; ++idx ) {
                    const menuBlockStyle = window.getComputedStyle(
                        menuBlocks[idx]);
                    if( menuBlockStyle.display != 'none' ) {
                        _showElement(toggle);
                        break;
                    }
                }
            }
        }
        if( pinned ) {
            sidebarParent.classList.remove('dashboard-pane-unpinned');
            sidebarParent.classList.add('dashboard-pane-pinned');
            for( let nextPinButton of
                 fullSidebar.nextElementSibling.querySelectorAll(
                     '.sidebar-pin-toggle') ) {
                const nextSidebarId = nextPinButton.dataset.target;
                togglePinSidebar(nextSidebarId, true);
            }
        } else {
            sidebarParent.classList.remove('dashboard-pane-pinned');
            sidebarParent.classList.add('dashboard-pane-unpinned');
            pinButtons = document.querySelectorAll('.sidebar-pin-toggle');
            for( let prevPinButton of pinButtons ) {
                const prevSidebarId = prevPinButton.dataset.target;
                if( prevSidebarId == fullSidebarId ) break;
                togglePinSidebar(prevSidebarId, false);
            }
        }
    }
}

function _onLoadDashboard() {
    for( let sidebarToggle of document.querySelectorAll('.sidebar-toggle') ) {
        sidebarToggle.addEventListener('click', function(evt) {
            evt.preventDefault();
            const elm = this;
            elm.classList.remove('sidebar-toggle-default');
            const fullSidebarId = elm.dataset.target;
            if( !fullSidebarId ) fullSidebarId = 'dashboard-navbar';
            toggleSidebar(fullSidebarId);
        });
    }

    for( let sidebarToggle of document.querySelectorAll('.sidebar-pin-toggle') ) {
        sidebarToggle.addEventListener('click', function(evt) {
            evt.preventDefault();
            const elm = this;
            const fullSidebarId = elm.dataset.target;
            if( !fullSidebarId ) fullSidebarId = 'dashboard-navbar';
            togglePinSidebar(fullSidebarId);
        });
    }

    window.addEventListener('resize', function() {
        for( let sidebarToggle of document.querySelectorAll('.sidebar-toggle') ) {
            for( child of sidebarToggle.children ) {
                child.classList.remove('opened');
                child.classList.add('closed');
            }
        }
    });
}

    if (document.readyState === "loading") {
        // The document is still loading, wait for the event
        document.addEventListener("DOMContentLoaded", _onLoadDashboard);
    } else {
        // The DOM is already ready (interactive or complete state)
        _onLoadDashboard();
    }

    // attach properties to the exports object to define
    // the exported module properties.
    exports.toggleSidebar = toggleSidebar;
    exports.togglePinSidebar = togglePinSidebar;
}));
