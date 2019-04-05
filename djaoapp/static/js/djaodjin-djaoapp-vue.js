if($('#theme-settings-container').length > 0){
var app = new Vue({
    el: "#theme-settings-container",
    mixins: [httpRequestMixin],
    data: {
        url: djaodjinSettings.urls.rules.api_detail,
        showEditTools: false
    },
    methods: {
        get: function(){
            var vm = this;
            vm.reqGet(vm.url, function(res){
                vm.showEditTools = res.show_edit_tools;
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
})
}
