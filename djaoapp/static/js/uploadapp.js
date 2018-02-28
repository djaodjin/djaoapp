/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

angular.module("StringFilter", []).filter("capitalize", function() {
    "use strict";
    return function(input, scope) {
        if( input != null ) {
            input = input.toLowerCase();
            return input.substring(0, 1).toUpperCase() + input.substring(1);
        }
    };
});

var app = angular.module("UploaderApp", ["StringFilter", "ngResource"]);

app.config(function($resourceProvider) {
  $resourceProvider.defaults.stripTrailingSlashes = false;
});

app.directive("errSrc", function() {
    "use strict";
    return {
        link: function(scope, element, attrs) {
            element.bind("error", function() {
                if (attrs.src !== attrs.errSrc) {
                    attrs.$set("src", attrs.errSrc);
                }
            });
        }
    };
});

app.directive("dropzone", function (csrf, s3) {
    "use strict";
    return function (scope, element, attrs) {
      var config, dropzone;

      config = scope[attrs.dropzone];
      var dropzoneUrl = config.options.url;
      if (s3.S3DirectUploadUrl){
        dropzoneUrl = s3.S3DirectUploadUrl;
      }

      $(".djaodjin-theme-upload-container").djupload({
        uploadUrl: dropzoneUrl,
        csrfToken: csrf.csrf_token,
        uploadZone: "body",
        uploadClickableZone: true,
        uploadParamName: "file",

        // S3 direct upload
        accessKey: s3.accessKey,
        mediaPrefix: s3.mediaPrefix,
        securityToken: s3.securityToken,
        policy: s3.policy,
        signature: s3.signature,
        amzCredential: s3.amzCredential,
        amzDate: s3.amzDate,

        // callback
        uploadSuccess: function(file, response){
          if (s3.S3DirectUploadUrl){
            $.ajax({
              method: "POST",
              url: config.options.url,
              data: {s3prefix: s3.mediaPrefix, file_name: file.name},
              success: function(response){
                scope.$apply(function() {
                  scope.themeList.results.push(response);
                });
                toastr.success("theme uploaded");
              }
            });
          }else{
            scope.$apply(function() {
              scope.themeList.results.push(response);
            });
            toastr.success("theme uploaded");
          }
          $(".dz-preview").remove();
        },

        uploadError: function(file, message){
          // dropzone sends it's own error messages in string
          message = message.message;
          var status = "browser";
          if( file.xhr ) {
              status = file.xhr.status;
          }
          toastr.error("Error " + status + ": " + message + " Please accept our apologies.");
        }
    });
   };
});

app.controller("UploaderCtrl",
function($scope, Themes, urls, csrf, $timeout, $filter) {
    "use strict";
    $scope.params = {};
    $scope.itemsPerPage = 25; // Must match on the server-side.
    $scope.maxSize = 5;      // Total number of pages to display
    $scope.currentPage = 1;
    $scope.totalItems = 0;

    $scope.refresh = function() {
        $scope.themeList = Themes.query($scope.params, function() {
            /* We cannot watch themeList.count otherwise things start
               to snowball. We must update totalItems only when
               it truly changed. */
            if( $scope.themeList.count != $scope.totalItems ) {
                $scope.totalItems = $scope.themeList.count;
            }
        });
    };
    $scope.refresh();

    $scope.pageChanged = function() {
        if( $scope.currentPage > 1 ) {
            $scope.params.page = $scope.currentPage;
        } else {
            delete $scope.params.page;
        }
        $scope.refresh();
    };

  $scope.activeTheme = urls.active_theme;
  $scope.detailView = false;
  $scope.dropzoneConfig = {
      "options": { // passed into the Dropzone constructor
          "url": urls.url_base_theme,
          "addRemoveLinks": true
      }};
  $scope.selectedTemplate = null;

  $scope.getTemplateDetail = function(id){
    console.log(id);
    $scope.detailView = true;
    var found = $filter("filter")($scope.themeList.results, {id: id}, true);
    if (found.length) {
      $scope.selectedTemplate = found[0];
    } else {
      $scope.selectedTemplate = "Not found";
    }
    // Apply theme
    $scope.selectedTemplate.is_active = true;
    $scope.selectedTemplate.$save();
  };

  $scope.closeDetailView = function(){
    $scope.detailView = false;
    $scope.selectedTemplate = null;
  };

});


app.factory("Themes", ["$resource", "urls",
  function($resource, urls){
    "use strict";
    return $resource(
      urls.url_base_theme + ":theme/", {"theme": "@slug"},
        {
          query: {method: "GET"},
          create: {method: "POST"},
          update: {method: "PUT"}
        });
  }
]);


