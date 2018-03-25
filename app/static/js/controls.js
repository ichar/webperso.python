// *******************************
// BANKPERSO PAGE CONTROLS MANAGER
// -------------------------------
// Version: 1.60
// Date: 14-02-2018

var STATUS = 'change-status';

var screen_size = [$_width('screen-max'), $_height('screen-max')];

// =================================
// Common Page Controls declarations
// =================================

var $Semaphore = {
    container    : null,

    IsTrace : 0, IsLog : 0,

    settings     : {
        'colors' : ['#0000ff', '#ff00ff', '#ffff00', '#ffa800', '#00ffff', '#00ff00', '#ff0000'],
        'background_color' : 'rgba(180, 180, 200, 0.1)',
        'default_class' : 'semaphore-default-item',
        'max_duration' : 10000,
    },

    template     : '',          // Kind of Semaphore Handle
    lid          : '',          // Handle LogID[OrderID:BatchID] to check state
    count        : 0,           // Number of indicators
    timeout      : 0,           // Timeout to windeow.setInterval
    action       : '',          // Handle action code
    speed        : [200, 600],  // Speed to animate indicators (on/off)
    items        : null,        // Semaphore indicator items (item objects list, this.item)

    index        : null,        // Index of interrupt mode

    is_active    : false,       // Initilized & ready to start, timeout is valid
    is_enabled   : false,       // Semaphore is active and Sidebar control is active & shown on the screen
    is_running   : false,       // Handle Web Servive is running
    is_focused   : true,        // Window is focused or not

    init: function(state) {
        if (state.length == 0) 
            return;

        this.updateState(state);

        if (this.IsLog)
            console.log('semaphore init');
    },

    reset: function(force) {
        this.items = new Array();

        for (i=0; i < this.count; i++) {
            if (force)
                this.items.push(this.item());

            var item = $("#semaphore-"+i.toString());
            if (!is_null(item)) {
                if (force)
                    item.removeClass(this.settings.default_class);
                else
                    item.addClass(this.settings.default_class);
            }
        }
    },

    updateState: function(state) {
        var x = state.split('::');
        var self = this;

        this.template = x[0];

        if (x.length > 1)
            this.lid = x[1] || '0:0';
        if (x.length > 2)
            this.count = parseInt(x[2]) || this.count || 7;
        if (x.length > 3)
            this.timeout = parseInt(x[3]) || this.timeout || 1000;
        if (x.length > 4)
            this.action = x[4] || this.action || '901';

        if (x.length > 5)
            x[5].split(':').forEach(function(s,i) { self.speed[i] = parseInt(s); });

        this.is_active = this.timeout > 0 ? true : false;

        if (this.IsTrace)
            alert(this.template+':'+this.lid+':'+this.count+':'+this.timeout+':'+this.action+':'+this.speed);
    },

    item: function() {
        return {'value':0, 'duration':0};
    },

    repr_item: function(i) {
        return this.items[i].value + ':' + this.items[i].duration;
    },

    dump: function() {
        var s = [];
        var self = this;

        if (is_null(this.items))
            return '';

        this.items.forEach(function(x, i) { s.push(self.repr_item(i)); });
        return s.join(',');
    },

    isEnabled: function() {
        this.is_enabled = $SidebarControl.isEnabled();
        return this.is_active & this.is_enabled & !this.is_running & this.is_focused;
    },

    toggleState: function() {
        if (this.isEnabled())
            this.start();
        else
            this.stop();
    },

    start: function(focused) {
        if (this.IsLog)
            console.log('semaphore start:'+this.index);

        // ---------------
        // Start semaphore
        // ---------------

        if (focused === true)
            this.is_focused = true;

        this.reset(1);

        interrupt(true, 9, $Semaphore.timeout, null, this.index, 1);
    },

    run: function(index) {
        this.index = index;
        
        if (!this.isEnabled()) {
            if (!this.is_running)
                this.stop();
            return;
        }

        if (this.IsLog)
            console.log('semaphore run:'+this.index);

        $web_semaphore(this.action);
    },

    stop: function(focused) {
        if (this.IsLog)
            console.log('semaphore stop:'+this.index, 'running:'+this.is_running, 'focused:'+this.is_focused);

        // --------------
        // Stop semaphore
        // --------------

        if (focused === false)
            this.is_focused = false;

        this.reset(0);

        interrupt(false, 0, 0, null, this.index, 1);
    },

    error: function() {
        this.stop();
        this.is_running = false;
    },

    running: function() {
        this.is_running = true;
    },

    refresh: function(ob) {
        this.is_running = false;

        if(is_null(ob))
            return;

        var state = ob['state'];
        var items = ob['items'];

        this.updateState(state);

        for (i=0; i < this.count; i++) {
            if (items.length == i)
                break;
            this.items[i] = items[i];
        }

        if (this.IsTrace)
            alert(this.dump());

        if (this.IsLog)
            console.log('semaphore refresh:'+this.dump());

        this.show();
    },

    show: function() {
        var self = this;
        var is_exist;

        do {
            is_exist = false;
            for (i=0; i < this.count; i++) {
                if (this.items[i].value > 0) {
                    var item = $("#semaphore-"+i.toString());

                    if (is_null(item))
                        continue;

                    var activate = this.speed[0];
                    var deactivate = this.items[i].duration || this.speed[1];

                    if (deactivate > 0 && deactivate < this.settings.max_duration) 
                        item.animate({backgroundColor:self.settings.colors[i]}, activate, function(){})
                            .animate({backgroundColor:self.settings.background_color}, deactivate);
                    else
                        item.animate({backgroundColor:self.settings.colors[i]}, activate);

                    this.items[i].value -= 1;
                    is_exist = true;
                }
            }
        } while(is_exist);
    }
};

var $SidebarControl = {
    container     : {'sidebar' : null, 'data' : null, 'panel' : null, 'navigator' : null, 'semaphore' : null},

    IsTrace : 0, IsLog : 0,

    timeout       : 600,
    timer         : null,
    
    default_position : {  // Should be the same as in common.html styles
        'margin_left' : ["50px", "422px"]
    },
    default_count : 4,

    state         : 0,    // Sidebar state: 0/1 - closed/opened
    data_margin   : 0,
    speed         : 400,
    is_active     : false,
    is_shown      : false,
    is_out        : false,
    is_run        : false,
    animated      : 0,

    callback      : null,

    init: function(callback) {
        this.callback = callback;

        this.container.sidebar = $("#sidebarFrame");
        this.container.data = $("#dataFrame");
        this.container.panel = $("#sidebar-content");
        this.container.navigator = $("#sidebar-navigator");
        this.container.semaphore = $("#semaphore");

        this.container.sidebar.css("min-height", ($_height('screen-min')-22).toString()+"px");

        this.state = parseInt($("#sidebar").val() || '0');

        this.initState();

        this.onBeforeStart();
    },

    initState: function() {
        var selection = $("#selected-batches");
        var parent = $("#line-table");
        var button = $("#CARDS_ACTIVATION");
        var box = $("#cards-selection-box");

        if (is_null(selection) || is_null(parent) || is_null(button) || is_null(box))
            return;

        //alert(BrowserDetect.browser+':'+BrowserDetect.version);

        box.css("width", button.width()+34);
        selection.css("height", parent.height()-38).css("width", button.width()+34);
    },

    getMargin: function() {
        return this.default_position.margin_left[this.state];
    },

    checkShown: function() {
        this.is_shown = this.state == 1 ? true : false;

        // --------------------
        // Parent page callback
        // --------------------

        if (!is_null(this.callback))
            this.callback();

        // -------------------------
        // Toggle state of semaphore
        // -------------------------

        $Semaphore.toggleState();
    },

    isEnabled: function() {
        return this.is_active & this.is_shown & this.state;
    },

    isDueAnimated: function() {
        return this.animated > 0 && this.animated < this.default_count ? true : false;
    },

    toggleFrame: function(force) {
        if (this.IsTrace)
            alert(this.state);

        if (this.isDueAnimated())
            return;

        if (!is_null(this.timer)) {
            clearTimeout(this.timer);
            this.timer = null;
        }

        var self = this;

        this.animated = 1;

        if (!force || (this.state == 1 && !this.is_shown) || (this.state == 0 && this.is_shown)) {
            this.container.semaphore
                .animate({ width:'toggle' }, this.speed, function() {}).promise().done(function() {
                    ++self.animated;
                });

            this.container.panel
                .animate({ width:'toggle' }, this.speed, function() {}).promise().done(function() {
                    ++self.animated;
                });

            this.container.navigator.toggleClass("sidebar-rotate");
        } else
            this.animated += 2;

        if (force)
            this.container.data
                .animate({ marginLeft:this.getMargin() }, this.speed, function() {}).promise().done(function() {
                    self.initState();
                    ++self.animated;
                });
        else
            this.animated += 1;

        if (this.IsLog)
            console.log('sidebar toggle frame:', this.animated, this.state, !this.is_shown);

        this.onToggle();
    },

    onBeforeStart: function() {
        setTimeout(function() { $SidebarControl.show(); }, 200);
    },

    onBeforeSubmit: function() {
        var state = this.state;
        $("input[name='sidebar']").each(function() { $(this).val(state) });

        if (this.is_shown && this.state == 0) {
            this.speed = 400;
            this.onFrameMouseOut();
        }
    },

    onFrameMouseOver: function(focused) {
        if (this.IsTrace)
            alert('over:'+this.state+':'+this.is_shown+':'+this.animated);

        if (!this.is_active || this.is_shown || this.state == 1 || this.isDueAnimated())
            return;

        this.is_out = false;

        this.timer = setTimeout(function() {
            var self = $SidebarControl;

            if (self.is_out) {
                self.is_out = false;
                return;
            }

            self.toggleFrame();

            self.is_shown = true;
            this.is_out = false;

            self.container.sidebar.addClass("sidebar-shadow");

            if (!is_null(focused))
                focused.focus();

        }, this.timeout);
    },

    hide: function() {
        if (this.state == 1)
            this.onNavigatorClick(false);
    },

    onFrameMouseOut: function() {
        if (this.IsTrace)
            alert('out:'+this.state+':'+this.is_shown+':'+this.animated);

        this.is_out = true;

        if (!this.is_active || !this.is_shown || this.state == 1 || this.isDueAnimated())
            return;
        
        this.toggleFrame();

        this.is_shown = false;
        this.is_out = false;

        this.container.sidebar.removeClass("sidebar-shadow");
    },

    onToggle: function() {
        if (typeof sidebar_toggle === 'function')
            sidebar_toggle();
    },

    onNavigatorClick: function(force) {
        if (self.is_run || this.isDueAnimated())
            return;

        if (force) {
            if (this.state == 0)
                this.container.navigator.toggleClass("sidebar-rotate");
            return;
        }

        self.is_run = true;

        this.state ^= 1;

        this.toggleFrame(true);

        this.container.sidebar.removeClass("sidebar-shadow");

        this.checkShown();

        self.is_run = false;
    },

    submit: function(frm) {
        this.onBeforeSubmit();
        frm.submit();
    },

    show: function() {
        this.is_active = true;
        this.checkShown();
    }
};

// ===========================
// Dialog windows declarations
// ===========================

var $StatusChangeDialog = {
    default_size : {'file'  : [710, screen_size[1]-140-(30*2)], /* 145 */
                    'batch' : [670, 385]
                   },

    container    : null,
    box          : null,
    actual_size  : new Object(),
    state        : new Object(),
    last         : null,

    IsTrace      : 0,

    min_width    : 500,
    min_height   : 200,

    offset_height_init   : 204,
    offset_height_resize : 114,
    offset_width_init    : 44,
    offset_width_resize  : 0,

    init: function() {
        this.container = $("#status-confirm-container");
        this.box = $("#status-confirmation-box");
        //this.actual_size = new Object();
        this.state = new Object();
        this.last = null;
    },

    get_id: function() {
        return this.container.attr('id');
    },

    get_mode: function() {
        return this.container.attr('mode');
    },

    set_mode: function(mode) {
        this.container.attr('mode', mode);
    },

    toggle: function(ob) {
        var oid = !is_null(ob) && ob.attr('id');

        if (this.last != null)
            $onToggleSelectedClass(STATUS, this.last, 'remove', null);

        if (this.IsTrace)
            alert('toggle:'+this.last+':'+oid);

        $onToggleSelectedClass(STATUS, ob, 'add', null);

        this.state['mode'] = this.get_mode();
        this.state['value'] = getsplitteditem(oid, ':', 1, '');

        this.last = ob;
    },

    setContent: function(id, data) {
        var mode = this.get_mode();

        $("#status-request").html(
            keywords['status confirmation']+' '+
            keywords['of '+mode]+
            ' ID:'+id+'? '+
            keywords['Recovery is impossible!']+' '+
            keywords['please confirm']
            );
        $("#status-confirmation").remove();

        var item = '<li class="change-status-item" id="status:ID">'+
                   '<dd class="change-status-id" id="change-status-id:ID">ID</dd>VALUE</li>';

        var content = '';

        data.forEach(function(x, index) {
            content += item
                .replace(/ID/g, x.id)
                .replace(/VALUE/g, x.value);
        });

        var html = 
            '<div class="common-confirmation" id="status-confirmation">'+
            '<h4>'+keywords['status confirmation request']+'</h4>'+
            '<div class="common-box"><div id="status-confirmation-box">'+
            '<ul class="status-'+mode+'">'+content+'</ul>'+
            '</div></div></div>';

        this.container.append(html);
        
        this.box = $("#status-confirmation-box");
    },

    setDefaultSize: function(force) {
        var mode = this.get_mode();

        if (!(mode in this.actual_size) || force)
            this.actual_size[mode] = this.default_size[mode];

        var size = this.actual_size[mode];

        if (this.IsTrace)
            alert('setDefaultSize:'+mode+':'+this.container.width()+':'+this.container.height()+':'+size+':'+force);

        this.container.dialog("option", "width", size[0]);
        this.container.dialog("option", "height", size[1]);

        // --------------------------------
        // Set default float content height
        // --------------------------------

        if (force)
            this.box
                //.css("width", size[0] - offset_width_init)
                .css("height", (size[1] - this.offset_height_init).toString()+"px");
    },

    onResize: function(force) {
        var mode = this.get_mode();

        if (!(mode in this.actual_size))
            return false;

        if (this.IsTrace)
            alert('resize:'+mode+':'+this.container.width()+':'+this.container.height()+':'+force);

        if (this.container.width() < this.min_width || this.container.height() < this.min_height) {
            this.setDefaultSize(true);
            return false;
        }

        // -------------------
        // Adjust float height
        // -------------------

        var offset = this.offset_height_resize;
        var new_height = this.container.height() - offset;

        this.box.css("height", new_height.toString()+"px");

        // -------------
        // Save new size
        // -------------

        if (force)
            this.actual_size[mode] = [
                this.container.width(), this.container.height() + offset + 5 // ???
            ];

        return true;
    },

    onOpen: function() {
        this.onResize(false);
        this.box.scrollTop(0);
    },

    onClose: function() {
        //this.actual_size[this.get_mode()] = [this.container.width(), this.container.height()];
    },

    confirmation: function(command) {
        this.init();

        var action = 
            command == 'admin:change-filestatus' ? '201' : (
            command == 'admin:change-batchstatus' ? '202' : null
            );

        if (this.IsTrace)
            alert('confirmation:'+action+':'+command);

        $web_logging(action);
    },

    submit: function() {
        $onParentFormSubmit();
    },

    open: function(action, data) {
        var mode = (action == '201' ? 'file' : 'batch');
        var id = SelectedGetItem(mode == 'file' ? LINE : SUBLINE, 'id');

        if (id == null)
            return;

        this.set_mode(mode);
        this.setContent(id, data);

        this.container.dialog("option", "title", keywords['Status confirmation form']);

        this.setDefaultSize(false);

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        this.container.dialog("open");
    },

    confirmed: function() {
        this.close();

        if (this.IsTrace)
            alert('confirmed:'+this.state['mode']);

        if (!('mode' in this.state))
            return;

        var mode = this.state['mode'];
        var id = SelectedGetItem((mode == 'file') ? LINE : SUBLINE, 'id');
        var value = this.state['value'];
        var command = 'admin:change-'+mode+'status';

        $("input[name='"+mode+"_id']").each(function() { $(this).val(id); });
        $("#status_"+mode+"_id").val(value);
        $("#command").val(command);

        this.submit();
    },

    close: function() {
        this.container.dialog("close");
    }
};

var $OrderDialog = {
    container    : null,
    box          : null,
    state        : new Object(),

    IsTrace      : 0,

    init: function() {
        this.container = $("#order-confirm-container");
        this.box = $("#order-request");
        this.state = new Object();
    },

    get_id: function() {
        return this.container.attr('id');
    },

    get_mode: function() {
        return this.container.attr('mode');
    },

    set_mode: function(mode) {
        this.container.attr('mode', mode);
    },

    toggle: function(ob) {
        this.state['mode'] = this.get_mode();
    },

    setContent: function(id, data) {
        var mode = this.get_mode();

        this.box.html(
            keywords['order confirmation']+' '+keywords[mode+' selected file']+
            ' ID:'+id+'? '+keywords['Recovery is impossible!']+' '+keywords['please confirm']
        );
    },

    submit: function() {
        $onParentFormSubmit();
    },

    open: function(command) {
        this.init();

        var mode = (command == 'admin:create') ? 'create' : 'delete';
        var id = SelectedGetItem(LINE, 'id');

        if (this.IsTrace)
            alert('open:'+command+':'+id);

        if (id == null)
            return;

        this.set_mode(mode);
        this.setContent(id, null);

        this.toggle(null);

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        this.container.dialog("open");
    },

    confirmed: function() {
        this.close();

        if (!('mode' in this.state))
            return;

        var mode = this.state['mode'];
        var id = SelectedGetItem(LINE, 'id');
        var command = 'admin:'+mode;

        $("input[name='file_id']").each(function() { $(this).val(id); });
        $("#command").val(command);

        this.submit();
    },

    close: function() {
        this.container.dialog("close");
    }
};

var $LogSearchDialog = {
    container : null,
    opened    : false,
    focused   : false,

    init: function() {
        this.container = $("#logsearch-confirm-container");
    },

    callback: function() {
        return this.container;
    },

    is_focused: function() {
        return (this.focused && !is_null(this.callback())) ? true : false;
    },

    submit: function() {
        $onParentFormSubmit();
    },

    open: function() {
        if (this.opened)
            return;

        this.init();

        this.opened = true;
        this.focused = true;

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        this.container.dialog("open");
    },

    onClose: function() {
        this.opened = false;
        this.focused = false;
    },

    confirmed: function() {
        this.focused = false;
        this.close();

        var command = 'admin:logsearch';
        var value =
            $("#logsearch-context").val()+
            '::'+($("#logsearch-apply-filter").prop('checked')? 1 : 0).toString()+
            '::'+($("#item-logsearch-exchange").prop('checked') ? 1 : 0).toString()+
            '::'+($("#item-logsearch-bankperso").prop('checked') ? 1 : 0).toString()+
            '::'+($("#item-logsearch-sdc").prop('checked') ? 1 : 0).toString()+
            '::'+($("#item-logsearch-infoexchange").prop('checked') ? 1 : 0).toString();
        $("#logsearched").val(value);
        $("#command").val(command);

        this.submit();
    },

    cancel: function() {
        this.focused = false;
        this.close();
    },

    close: function() {
        this.container.dialog("close");
        this.onClose();
    }
};

var $TagSearchDialog = {
    container : null,
    opened    : false,
    focused   : false,

    init: function() {
        this.container = $("#tagsearch-confirm-container");
    },

    callback: function() {
        return this.container;
    },

    is_focused: function() {
        return (this.focused && !is_null(this.callback())) ? true : false;
    },

    submit: function() {
        $onParentFormSubmit();
    },

    open: function() {
        if (this.opened)
            return;

        this.init();

        this.opened = true;
        this.focused = true;

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        this.container.dialog("open");
    },

    onClose: function() {
        this.opened = false;
        this.focused = false;
    },

    confirmed: function() {
        this.focused = false;
        this.close();

        var command = 'admin:tagsearch';
        var value =
            $("#tagsearch-context").val();
        $("#tagsearched").val(value);
        $("#command").val(command);

        this.submit();
    },

    cancel: function() {
        this.focused = false;
        this.close();
    },

    close: function() {
        this.container.dialog("close");
        this.onClose();
    }
};

var $ConfirmDialog = {
    container : null,
    opened    : false,
    focused   : false,

    init: function() {
        this.container = $("#confirm-container");
    },

    is_focused: function() {
        return this.focused;
    },

    open: function(msg, width, height) {
        if (this.opened)
            return;

        this.init();

        this.opened = true;
        this.focused = true;

        this.setContent(msg);

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        if (width)
            this.container.dialog("option", "width", width);
        if (height)
            this.container.dialog("option", "height", height);

        this.container.dialog("open");
    },

    onClose: function() {
        this.opened = false;
        this.focused = false;
    },

    setContent: function(msg) {
        var box = $("#confirm-info");
        var s = '<p>'+msg.replace(/{/g, '<').replace(/}/g, '>')+'</p>';

        isConfirmation = true;

        box.html(s);
    },

    cancel: function() {
        this.focused = false;
        this.close();
    },

    close: function() {
        isConfirmation = false;

        this.container.dialog("close");
        this.onClose();
    }
};

var $NotificationDialog = {
    container : null,

    opened    : false,
    focused   : false,

    init: function() {
        this.container = $("#notification-container");
    },

    is_focused: function() {
        return this.focused;
    },

    open: function(msg, width, height) {
        if (this.opened)
            return;

        this.init();

        this.opened = true;
        this.focused = true;

        this.setContent(msg);

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        if (width)
            this.container.dialog("option", "width", width);
        if (height)
            this.container.dialog("option", "height", height);

        this.container.dialog("open");
    },

    onClose: function() {
        this.opened = false;
        this.focused = false;
    },

    setContent: function(msg) {
        var box = $("#notification-info");
        var s = '<p>'+msg.replace(/{/g, '<').replace(/}/g, '>')+'</p>';

        isNotificationation = true;

        box.html(s);
    },

    cancel: function() {
        this.focused = false;
        this.close();
    },

    close: function() {
        isNotificationation = false;

        this.container.dialog("close");
        this.onClose();
    }
};

var $HelpDialog = {
    container : null,
    context   : null,
    opened    : false,

    init: function() {
        this.container = $("#help-container");
        this.context = $CurrentContext();
    },

    open: function() {
        if (this.opened)
            return;

        this.init();

        this.opened = true;

        this.confirmed();

        //this.container.dialog("option", "position", {my:"center center", at:"center center", of:"#dataFrame"});

        this.container.dialog("open");
    },

    onClose: function() {
        this.opened = false;
    },

    confirmed: function() {
        var box = $("#help-info");
        var s = '<p class="group">'+'Общие команды интерфейса'+':</p>'+
                //'<div><dt class="keycode">Shift-F1</dt><dd class="spliter">:</dd><p class="text">'+'Данная справка'+'</p></div>'+
                '<div><dt class="keycode">Shift-O/C</dt><dd class="spliter">:</dd><p class="text">'+'Развернуть/свернуть панель меню'+'</p></div>'+
                //'<div><dt class="keycode">F5</dt><dd class="spliter">:</dd><p class="text">'+'Команда "Обновить данные"'+'</p></div>'+
                //'<div><dt class="keycode">Ctrl-F5</dt><dd class="spliter">:</dd><p class="text">'+'Команда "Обновить интерфейс (перезагрузка)"'+'</p></div>'+
                '<p class="group">'+'Журнал (заказы/файлы)'+':</p>'+
                '<div><dt class="keycode">Ctrl/Shift-Up/Down</dt><dd class="spliter">:</dd><p class="text">'+'назад/вперед на одну строку'+'</p></div>'+
                //'<div><dt class="keycode">Ctrl/Shift-Down</dt><dd class="spliter">:</dd><p class="text">'+'вперед на одну строку'+'</p></div>'+
                '<div><dt class="keycode">Ctrl-Home/End</dt><dd class="spliter">:</dd><p class="text">'+'к первой/последней странице'+'</p></div>'+
                //'<div><dt class="keycode">Ctrl-End</dt><dd class="spliter">:</dd><p class="text">'+'к последней странице'+'</p></div>'+
                '<div><dt class="keycode">Shift-PgUp/PgDown</dt><dd class="spliter">:</dd><p class="text">'+'к предыдущей/следующей странице'+'</p></div>'+
                //'<div><dt class="keycode">Shift-PgDown</dt><dd class="spliter">:</dd><p class="text">'+'к следующей странице'+'</p></div>'+
                '<p class="group">'+'ИнфоБлок (партии/события)'+':</p>'+
                '<div><dt class="keycode">Alt-Up/Down</dt><dd class="spliter">:</dd><p class="text">'+'назад/вперед на одну строку'+'</p></div>'+
                //'<div><dt class="keycode">Alt-Down</dt><dd class="spliter">:</dd><p class="text">'+'вперед на одну строку'+'</p></div>'+
                '<div><dt class="keycode">Alt-PgUp/PgDown</dt><dd class="spliter">:</dd><p class="text">'+'к первой/последней строке'+'</p></div>'+
                //'<div><dt class="keycode">Alt-PgDown</dt><dd class="spliter">:</dd><p class="text">'+'к последней строке'+'</p></div>'+
                '<p class="group">'+'ИнфоМеню (вкладки)'+':</p>'+
                '<div><dt class="keycode">Shift-Tab</dt><dd class="spliter">:</dd><p class="text">'+'к следующей вкладке (в цикле)'+'</p></div>'+
                '<div><dt class="keycode">Ctrl-Left/Right</dt><dd class="spliter">:</dd><p class="text">'+'к предыдущей/следующей вкладке'+'</p></div>'+
                //'<div><dt class="keycode">Ctrl-Right</dt><dd class="spliter">:</dd><p class="text">'+'к следующей вкладке'+'</p></div>'+
                '<p class="group">'+'Функциональные команды'+':</p>';

        if (['bankperso'].indexOf(this.context) > -1) {
            s +=
                '<div><dt class="keycode">Shift-L</dt><dd class="spliter">:</dd><p class="text">'+'Поиск по журналам персосети'+'</p></div>'+
                '<div><dt class="keycode">Shift-P</dt><dd class="spliter">:</dd><p class="text">'+'Печать ТЗ'+'</p></div>';
        }

        if (['cards'].indexOf(this.context) > -1) {
            s +=
                '<div><dt class="keycode">Shift-A</dt><dd class="spliter">:</dd><p class="text">'+'Активировать партии файла'+'</p></div>'+
                '<div><dt class="keycode">Shift-P</dt><dd class="spliter">:</dd><p class="text">'+'Печать документов'+'</p></div>';
        }

            s +=
                '<div><dt class="keycode">Shift-R</dt><dd class="spliter">:</dd><p class="text">'+'Сбросить фильтр'+'</p></div>'+
                '<div><dt class="keycode">Shift-S</dt><dd class="spliter">:</dd><p class="text">'+'Контекстный поиск'+'</p></div>';

        if (['bankperso','cards'].indexOf(this.context) > -1) {
            s +=
                '<div><dt class="keycode">Shift-T</dt><dd class="spliter">:</dd><p class="text">'+'Фильтр текущего дня'+'</p></div>'+
                '';
        }

        if (['configurator'].indexOf(this.context) > -1) {
            s +=
                '<div><dt class="keycode">Shift-I</dt><dd class="spliter">:</dd><p class="text">'+'Добавить параметр'+'</p></div>'+
                '<div><dt class="keycode">Shift-U</dt><dd class="spliter">:</dd><p class="text">'+'Редактировать параметр'+'</p></div>'+
                '<div><dt class="keycode">Shift-D</dt><dd class="spliter">:</dd><p class="text">'+'Удалить параметр'+'</p></div>'+
                '';
        }

        box.html(s);
    },

    cancel: function() {
        this.close();
    },

    close: function() {
        this.container.dialog("close");
        this.onClose();
    }
};

// =======
// Dialogs
// =======

jQuery(function($) 
{
    // --------------------
    // Status Change Dialog
    // --------------------

    $("#status-confirm-container").dialog({
        autoOpen: false,
        buttons: [
            {text: keywords['Confirm'], click: function() { $StatusChangeDialog.confirmed(); }},
            {text: keywords['Reject'],  click: function() { $StatusChangeDialog.close(); }}
        ],
        modal: true,
        draggable: true,
        resizable: true,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        open: function() {
            $StatusChangeDialog.onOpen();
        },
        close: function() {
            $StatusChangeDialog.onClose();
        },
        resize: function() {
            $StatusChangeDialog.onResize(true);
        }
    });

    // ----------------------------
    // Order Recreate/Remove Dialog
    // ----------------------------

    $("#order-confirm-container").dialog({
        autoOpen: false,
        width:540, // 640
        height:150, // 136
        position:0,
        buttons: [
            {text: keywords['Confirm'], click: function() { $OrderDialog.confirmed(); }},
            {text: keywords['Reject'],  click: function() { $OrderDialog.close(); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
    });

    // -----------------
    // Log Search Dialog
    // -----------------

    $("#logsearch-confirm-container").dialog({
        autoOpen: false,
        width:540,
        height:420,
        position:0,
        buttons: [
            {text: keywords['Run'],    click: function() { $LogSearchDialog.confirmed(); }},
            {text: keywords['Reject'], click: function() { $LogSearchDialog.cancel(); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $LogSearchDialog.onClose();
        }
    });

    // -----------------
    // Tag Search Dialog
    // -----------------

    $("#tagsearch-confirm-container").dialog({
        autoOpen: false,
        width:590,
        height:270,
        position:0,
        buttons: [
            {text: keywords['Run'],    click: function() { $TagSearchDialog.confirmed(); }},
            {text: keywords['Reject'], click: function() { $TagSearchDialog.cancel(); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $TagSearchDialog.onClose();
        }
    });

    // ---------------
    // Help form: <F1>
    // ---------------

    $("#help-container").dialog({
        autoOpen: false,
        width:560,
        height:642, /* 720 = 25 for one line */
        //position:0,
        buttons: [
            {text: keywords['OK'], click: function() { $HelpDialog.cancel(); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $HelpDialog.onClose();
        }
    });

    // --------------------
    // Confirm form: Yes/No
    // --------------------

    $("#confirm-container").dialog({
        autoOpen: false,
        width:400,
        //height:600,
        //position:0,
        buttons: [
            {text: keywords['yes'], click: function() { $Confirm(1, $(this)); }},
            {text: keywords['no'], click: function() { $Confirm(0, $(this)); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $ConfirmDialog.onClose();
        }
    });

    // ----------------------
    // Notification form: Yes
    // ----------------------

    $("#notification-container").dialog({
        autoOpen: false,
        width:400,
        //height:600,
        //position:0,
        buttons: [
            {text: keywords['OK'], click: function() { $Notification(1, $(this)); }},
        ],
        modal: true,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $NotificationDialog.onClose();
        }
    });
});
