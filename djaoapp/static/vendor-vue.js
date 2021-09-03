// moment.js is are `function (root, factory) {` modules
import moment from 'moment';
window.moment = moment;
import 'moment-timezone/builds/moment-timezone-with-data.js';

// Use 'vue/dist/vue.esm.js' compiler+runtime ESM module otherwise
// the `/profile/{organization}/subscribers/` page does not display correctly
// and no error is shown in the console log.
import Vue from 'vue';
window.Vue = Vue;

// Use sortablejs ESM module
// because of statement `new Sortable(el, binding.value || {})`
// in djaodjin-rules-vue.js
import Sortable from 'sortablejs';
window.Sortable = Sortable;

// Use 'uiv/dist/uiv.esm.js' ESM module?
// because of:
//  - <uiv-dropdown> and <uiv-date-picker> in jinja2/_form_fields.html
//  - <uiv-typeahead> in saas/profile/plans/subscribers.html
//  - <uiv-typeahead> in saas/profile/roles/role.html
//  - <uiv-typeahead> in saas/users/roles.html
//  - <uiv-typeahead> in saas/billing/import.html
// XXX This should be removed since uiv only supports Bootstrap3.
import * as uiv from 'uiv';
window.uiv = uiv;

import Croppa from 'vue-croppa';
window.Croppa = Croppa;

import InfiniteLoading from 'vue-infinite-loading';
window.InfiniteLoading = InfiniteLoading;

import _ from 'lodash';
window._ = _;

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
