/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* jshint multistr: true */

var snaplinesAPI = {
    /* XXX merely loading this file will register event handler on the whole
       document instead of being explicitedy done in a local document.ready
       handler. */
    urls: {
            "api_editable_update": "/api/editables",
            "api_wizard_next": "",
            "saas_api_plan": "/api/plans"
        },

    init: function(organization, urls) {
        this.urls = {
            "api_editable_update": "/api/" + organization + "/editables",
            "api_wizard_next": "",
            "saas_api_plan": "/" + organization + "/api/plans"
        };
        jQuery.extend(this.urls, urls);
        initWizard(this.urls.api_wizard_next);
    }
};


/** Add a button to move to the next step of a Wizard.
 */
function initWizard(nextUrl) {
    "use strict";
    if( nextUrl ) {
        var arrowNextStep = "<div class=\"wizard-menu next-wizard\" data-intro=\"Follow the wizard\" data-position=\"left\"><a href=\"" + nextUrl + "\"><i class=\"fa fa-angle-double-right\"></i></a></div>";
        $("body").append(arrowNextStep);
    }
}
