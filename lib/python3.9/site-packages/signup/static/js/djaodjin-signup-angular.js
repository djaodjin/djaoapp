/*=============================================================================
  App
  ============================================================================*/
var signupApp = angular.module("signupApp", ["ui.bootstrap",
    "ngRoute", "signupControllers"]);

//=============================================================================
// Controllers
//============================================================================
var signupControllers = angular.module("signupControllers", []);

signupControllers.controller("itemListCtrl",
    ["$scope", "$http", "$timeout", "settings",
     function($scope, $http, $timeout, settings) {
    "use strict";
    $scope.items = {};
    $scope.totalItems = 0;

    $scope.resetDefaults = function(overrides) {
        $scope.dir = {};
        var opts = {};
        if( settings.sortByField ) {
            opts['o'] = settings.sortByField;
            opts['ot'] = settings.sortDirection || "desc";
            $scope.dir[settings.sortByField] = opts['ot'];
        }
        if( settings.date_range ) {
            if( settings.date_range.start_at ) {
                opts['start_at'] = moment(settings.date_range.start_at).toDate();
            }
            if( settings.date_range.ends_at ) {
                opts['ends_at'] = moment(settings.date_range.ends_at).toDate()
            }
        }
        $scope.filterExpr = "";
        $scope.itemsPerPage = settings.itemsPerPage; // Must match server-side
        $scope.maxSize = 5;               // Total number of direct pages link
        $scope.currentPage = 1;
        // currentPage will be saturated at maxSize when maxSize is defined.
        $scope.formats = ["dd-MMMM-yyyy", "yyyy/MM/dd",
            "dd.MM.yyyy", "shortDate"];
        $scope.format = $scope.formats[0];
        $scope.opened = { "start_at": false, "ends_at": false };
        if( typeof overrides === "undefined" ) {
            overrides = {};
        }
        $scope.params = angular.merge({}, opts, overrides);
    };

    $scope.resetDefaults();

    // calendar for start_at and ends_at
    $scope.open = function($event, date_at) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.opened[date_at] = true;
    };

    // Generate a relative date for an instance with a ``created_at`` field.
    $scope.relativeDate = function(at_time) {
        var cutOff = new Date();
        if( $scope.params.ends_at ) {
            cutOff = new Date($scope.params.ends_at);
        }
        var dateTime = new Date(at_time);
        if( dateTime <= cutOff ) {
            return moment.duration(cutOff - dateTime).humanize() + " ago";
        } else {
            return moment.duration(dateTime - cutOff).humanize() + " left";
        }
    };

    $scope.$watch("params", function(newVal, oldVal, scope) {
        var updated = (newVal.o !== oldVal.o || newVal.ot !== oldVal.ot
            || newVal.q !== oldVal.q || newVal.page !== oldVal.page );
        if( (typeof newVal.start_at !== "undefined")
            && (typeof newVal.ends_at !== "undefined")
            && (typeof oldVal.start_at !== "undefined")
            && (typeof oldVal.ends_at !== "undefined") ) {
            /* Implementation Note:
               The Date objects can be compared using the >, <, <=
               or >= operators. The ==, !=, ===, and !== operators require
               you to use date.getTime(). Don't ask. */
            if( newVal.start_at.getTime() !== oldVal.start_at.getTime()
                && newVal.ends_at.getTime() === oldVal.ends_at.getTime() ) {
                updated = true;
                if( $scope.params.ends_at < newVal.start_at ) {
                    $scope.params.ends_at = newVal.start_at;
                }
            } else if( newVal.start_at.getTime() === oldVal.start_at.getTime()
                       && newVal.ends_at.getTime() !== oldVal.ends_at.getTime() ) {
                updated = true;
                if( $scope.params.start_at > newVal.ends_at ) {
                    $scope.params.start_at = newVal.ends_at;
                }
            }
        }

        if( updated ) {
            $scope.refresh();
        }
    }, true);

    $scope.filterList = function(regex) {
        if( regex ) {
            if ("page" in $scope.params){
                delete $scope.params.page;
            }
            $scope.params.q = regex;
        } else {
            delete $scope.params.q;
        }
    };

    $scope.pageChanged = function() {
        if( $scope.currentPage > 1 ) {
            $scope.params.page = $scope.currentPage;
        } else {
            delete $scope.params.page;
        }
    };

    $scope.sortBy = function(fieldName) {
        if( $scope.dir[fieldName] == "asc" ) {
            $scope.dir = {};
            $scope.dir[fieldName] = "desc";
        } else {
            $scope.dir = {};
            $scope.dir[fieldName] = "asc";
        }
        $scope.params.o = fieldName;
        $scope.params.ot = $scope.dir[fieldName];
        $scope.currentPage = 1;
        // pageChanged only called on click?
        delete $scope.params.page;
    };

    $scope.refresh = function() {
        $http.get(settings.urls.api_items,
            {params: $scope.params}).then(
            function(resp) {
                // We cannot watch items.count otherwise things start
                // to snowball. We must update totalItems only when it truly
                // changed.
                if( resp.data.count != $scope.totalItems ) {
                    $scope.totalItems = resp.data.count;
                }
                $scope.items = resp.data;
                $scope.items.$resolved = true;
            }, function(resp) {
                $scope.items = {};
                $scope.items.$resolved = false;
                showErrorMessages(resp);
                $http.get(settings.urls.api_items,
                    {params: angular.merge({force: 1}, $scope.params)}).then(
                function success(resp) {
                    // ``force`` load will not call the processor backend
                    // for reconciliation.
                    if( resp.data.count != $scope.totalItems ) {
                        $scope.totalItems = resp.data.count;
                    }
                    $scope.items = resp.data;
                    $scope.items.$resolved = true;
                });
            });
    };

    if( settings.autoload ) {
        $scope.refresh();
    }
}]);


signupControllers.controller("contactCtrl",
    ["$scope", "$controller", "$http", "$timeout", "settings",
     function($scope, $controller, $http, $timeout, settings) {
    "use strict";
    var opts = angular.merge({
        autoload: true,
        sortByField: "created_at",
        sortDirection: "desc",
        urls: {api_items: settings.urls.api_activities}}, settings);
    $controller("itemListCtrl", {
        $scope: $scope, $http: $http, $timeout:$timeout, settings: opts});

    $scope.activity = {text: ""};

    $scope.createActivity = function() {
        $http.post(settings.urls.api_activities, $scope.activity).then(
            function(resp) {
                $scope.refresh();
            },
            function(resp) {
                showErrorMessages(resp);
            }
        );
    }

    $scope.getCandidates = function(val) {
        if( typeof settings.urls.api_candidates === "undefined" ) {
            return [];
        }
        return $http.get(settings.urls.api_candidates, {
            params: {q: val}
        }).then(function(res){
            return res.data.results;
        });
    };
}]);


signupControllers.controller("contactsCtrl",
    ["$scope", "$controller", "$http", "$timeout", "settings",
     function($scope, $controller, $http, $timeout, settings) {
    "use strict";
    var opts = angular.merge({
        autoload: true,
        sortByField: "created_at",
        sortDirection: "desc",
        urls: {api_items: settings.urls.api_contacts}}, settings);
    $controller("itemListCtrl", {
        $scope: $scope, $http: $http, $timeout:$timeout, settings: opts});

    $scope.contact = {full_name: "", nick_name: "", email: ""};

    $scope.createContact = function() {
        $http.post(settings.urls.api_contacts, $scope.contact).then(
            function(resp) {
                window.location = settings.urls.contacts + resp.data.slug + '/';
            },
            function(resp) {
                showErrorMessages(resp);
            }
        );
    }
}]);


signupControllers.controller("userProfileCtrl",
    ["$scope", "$element", "$controller", "$http", "$timeout", "settings",
    function($scope, $element, $controller, $http, $timeout, settings) {

    $scope.password = "";
    $scope.api_key = "Generating ...";

    $scope.generateKey = function(event, dialog) {
        var passwordDialog = jQuery(event.target).parents('.modal');
        if( passwordDialog ) {
            if( passwordDialog.data('bs.modal') ) {
                passwordDialog.modal("hide");
            }
        }
        $http.post(settings.urls.user.api_generate_keys, {
           password: $scope.password}).then(
           function success(resp) {
               $scope.password = "";
               $scope.api_key = resp.data.secret;
               if( dialog ) {
                   var showKey = jQuery(dialog);
                   showKey.modal("show");
               }
           },
           function error(resp) {
               $scope.password = "";
               $scope.api_key = "ERROR";
               showErrorMessages(resp);
           });
    };

    $scope.deleteProfile = function(event) {
        event.preventDefault();
        $http.delete(settings.urls.user.api_profile).then(
        function(resp) { // success
            // When we DELETE the request.user profile, it will lead
            // to a logout. When we delete a different profile, a reload
            // of the page leads to a 404. In either cases, moving on
            // to the redirect_to_profile page is a safe bet. */
            window.location = settings.urls.user.profile_redirect;
        }, function(resp) { // error
            showErrorMessages(resp);
        });
   };

}]);
