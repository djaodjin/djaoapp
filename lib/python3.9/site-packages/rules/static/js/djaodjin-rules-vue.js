Vue.directive('sortable', {
  bind: function (el, binding) {
    Sortable.create(el, binding.value || {})
  },
})

var DATE_FORMAT = 'MMM DD, YYYY';


Vue.component('rules-table', {
    mixins: [
        itemListMixin,
        paginationMixin,
    ],
    data: function(){
        return {
            url: this.$urls.rules.api_rules,
            ruleModalOpen: false,
            newRule: {
                path: '',
                rank: 0,
                is_forward: false,
            },
            edit_description: [],
        }
    },
    methods: {
        moved: function(event){
            var vm = this;
            var oldRank = vm.items.results[event.oldIndex].rank;
            var newRank = vm.items.results[event.newIndex].rank;
            var pos = [{oldpos: oldRank, newpos: newRank}];
            vm.reqPatch(vm.url, {"updates": pos},
            function (resp) {
                vm.items.results.splice(event.newIndex, 0,
                    vm.items.results.splice(event.oldIndex, 1)[0]);
                for( var idx = 0; idx < vm.items.results; ++idx ) {
                    vm.items.results[idx].rank = resp.results[rank];
                }
            });
        },
        create: function(){
            var vm = this;
            vm.reqPost(vm.url, vm.newRule,
            function (resp) {
                vm.get();
                vm.newRule = {
                    path: '',
                    rank: 0,
                    is_forward: false,
                }
                vm.ruleModalOpen = false;
            },
            function(resp){
                vm.ruleModalOpen = false;
                showErrorMessages(resp);
            });
        },
        update: function(rule){
            var vm = this;
            vm.reqPut(vm.url + rule.path, rule,
            function (resp) {
                vm.ruleModalOpen = false;
            },
            function(resp){
                vm.ruleModalOpen = false;
                showErrorMessages(resp);
            });
        },
        remove: function(idx){
            var vm = this;
            var rule = vm.items.results[idx]
            vm.reqDelete(vm.url + rule.path,
            function (resp) {
                vm.params.page = 1;
                vm.get();
            });
        },
        editDescription: function(idx){
            var vm = this;
            vm.edit_description = Array.apply(
                null, new Array(vm.items.results.length)).map(function() {
                return false;
            });
            vm.$set(vm.edit_description, idx, true)
            // at this point the input is rendered and visible
            vm.$nextTick(function(){
                vm.$refs.edit_description_input[idx].focus();
            });
        },
        saveDescription: function(coupon, idx, event){
            if (event.which === 13 || event.type === "blur" ){
                this.$set(this.edit_description, idx, false)
                this.update(this.items.results[idx])
            }
        },
    },
    mounted: function(){
        this.get();
    }
});

// XXX Connects to bootstrap.js should be somewhere else.
$('#new-rule').on('shown.bs.modal', function(){
    var self = $(this);
    self.find('[name="new_rule_path"]').focus();
});


Vue.component('rule-list', {
    mixins: [
        itemMixin,
    ],
    data: function() {
        return {
            url: this.$urls.rules.api_detail,
            api_generate_key_url: this.$urls.rules.api_generate_key,
            api_session_data_url: this.$urls.rules.api_session_data,
            sessionKey: gettext('Generating...'),
            testUsername: '',
            forward_session: '',
            forward_session_header: '',
            forward_url: '',
        }
    },
    methods: {
        generateKey: function(){
            var vm = this;
            vm.reqPost(vm.api_generate_key_url,
            function (resp) {
                vm.sessionKey = resp.enc_key;
            },
            function(resp) {
                vm.sessionKey = gettext("ERROR");
                showErrorMessages(resp);
            });
        },
        getSessionData: function(){
            var vm = this;
            vm.reqGet(vm.api_session_data_url + "/" + vm.testUsername,
            function(resp) {
                vm.forward_session = resp.forward_session;
                vm.forward_session_header = resp.forward_session_header;
                vm.forward_url = resp.forward_url;
            });
        },
        update: function(submitEntryPoint) {
            var vm = this;
            var data = {
                authentication: vm.$refs.authentication.value,
                welcome_email: vm.$refs.welcomeEmail.checked,
                session_backend: vm.$refs.sessionBackend.value,
            }
            if( submitEntryPoint ) {
                data['entry_point'] = vm.$refs.entryPoint.value;
            }
            vm.reqPut(vm.url, data,
            function (resp) {
                showMessages([gettext("Update successful.")], "success");
            });
        },
    },
});


Vue.component('user-engagement', {
    mixins: [
        itemListMixin,
    ],
    data: function() {
        return {
            url: this.$urls.rules.api_user_engagement,
        }
    },
    computed: {
        tags: function(){
            var tags = [];
            this.items.results.forEach(function(e){
                tags = tags.concat(e.engagements).filter(function(value, index, self){
                    return self.indexOf(value) === index;
                });
            });
            return tags;
        }
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('user-aggregate-engagement', {
    mixins: [
        itemMixin
    ],
    data: function(){
        return {
            url: this.$urls.rules.api_engagement,
            getCb: 'getAndChart',
        }
    },
    methods: {
        getAndChart: function(resp){
            var vm = this;
            vm.item = resp;
            vm.itemLoaded = true;
            var el = vm.$refs.engagementChart;

            // nvd3 is available on djaoapp
            if(vm.item.engagements.length === 0 || !el || !nv) return;

            nv.addGraph(function() {
                var data = [{
                    "key": "Engagements",
                    "values": vm.item.engagements.map(function(e){
                      return {
                        "label": e.slug,
                        "value" : e.count
                      }
                    })
                }];
                var chart = nv.models.multiBarHorizontalChart()
                    .x(function(d) { return d.label })
                    .y(function(d) { return d.value })
                    .barColor(nv.utils.defaultColor())
                    .valueFormat(function (d) {
                        return d3.format(',.1f')(d) + '%'; })
                    .showValues(true)
                    .showLegend(false)
                    .showControls(false)
                    .showXAxis(false)
                    .showYAxis(false)
                    .groupSpacing(0.02)
                    .margin({top: 0, right: 0, bottom: 0, left: 0});

                d3.select(el)
                    .datum(data)
                    .call(chart);

                // centering logic
                var height = parseInt(d3.select(".positive rect").attr('height'));
                var y = (height / 2) + 3; // 3 is a magic number
                // add labels inside bars
                d3.selectAll(".positive").append("text")
                    .style('fill', 'white')
                    .text(function(d){ return d.label })
                    .attr('x', '10')
                    .attr('y', y)

                chart.tooltip.enabled(false);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        },
    },
    mounted: function(){
        this.get();
    }
});

