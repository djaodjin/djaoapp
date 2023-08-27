
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

    function setThemeColorMode(colorMode) {
        if (colorMode === 'auto' && window.matchMedia(
            '(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-bs-theme', 'dark')
        } else {
            document.documentElement.setAttribute('data-bs-theme', colorMode)
        }
    }

    // Stores the user preference in localStorage so it gets applied
    // on each page load.
    function getStoredThemeColorMode() {
        return localStorage.getItem('theme');
    }

    function setStoredThemeColorMode(colorMode) {
        localStorage.setItem('theme', colorMode)
    }

    function getPreferredThemeColorMode() {
        const colorMode = getStoredThemeColorMode()
        if( colorMode ) {
            return colorMode;
        }
        return window.matchMedia(
            '(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    // Dynamically set/update theme color mode.
    setThemeColorMode(getPreferredThemeColorMode());

    window.addEventListener('DOMContentLoaded', () => {

        document.querySelectorAll('[data-bs-theme-value]')
            .forEach(toggle => {
                toggle.addEventListener('click', () => {
                    const colorMode = toggle.getAttribute('data-bs-theme-value')
                    setStoredThemeColorMode(colorMode);
                    setThemeColorMode(colorMode);
                })
            })
    })

    // attach properties to the exports object to define
    // the exported module properties.
    exports.setThemeColorMode = setThemeColorMode;

}));
