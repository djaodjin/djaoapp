Vue.component('role-user-list-modal', {
    methods: {
        create: function() {
            var dialog = $(".create-profile");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("show");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("show");
               }
            }
        },
        createCompleted: function() {
            var dialog = $(".create-profile");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("hide");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("hide");
               }
            }
        },
        invite: function() {
            var dialog = $(".add-role-modal");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("show");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("show");
               }
            }
        },
        inviteCompleted: function() {
            var dialog = $(".add-role-modal");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("hide");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("hide");
               }
            }
        }
    }
});


Vue.component('theme-update', {
    mixins: [
        httpRequestMixin
    ],
    data: function() {
        return {
            url: djaodjinSettings.urls.rules.api_detail,
            showEditTools: false
        }
    },
    methods: {
        get: function() {
            var vm = this;
            vm.reqGet(vm.url, function(res){
                vm.showEditTools = res.show_edit_tools;
            });
        },
        reset: function() {
            var vm = this;
            vm.reqDelete(djaodjinSettings.urls.pages.api_themes,
            function(resp) {
                showMessages([gettext("reset to default theme")], "success");
            });
        },
        save: function(){
            var vm = this;
            vm.reqPut(vm.url, {
                    show_edit_tools: vm.showEditTools,
                },
                function(){
                    location.reload();
                }
            );
        },
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('recent-activity', {
    mixins: [
        itemListMixin
    ],
    data: function(){
        return {
            url: djaodjinSettings.urls.recent_activity,
        }
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('todo-list', {
    mixins: [
        itemListMixin
    ],
    data: function(){
        return {
            url: djaodjinSettings.urls.api_todos,
        }
    },
    mounted: function(){
        this.get();
    },
});
