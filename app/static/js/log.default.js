// ***************************
// HELPER PAGE DEFAULT CONTENT
// ---------------------------
// Version: 1.10
// Date: 22-07-2017

// -----------------
// Log page handlers
// -----------------

var $ProfileClients = {
    selected_left_item  : null,
    selected_right_item : null,

    item_clients_all    : null,
    left_panel          : null,
    right_panel         : null,
    button_include      : null,
    button_exclude      : null,

    IsTrace    : 0,

    items      : new Object(),
    left_side  : null,
    right_side : null,

    init: function() {
        this.selected_left_item = null;
        this.selected_right_item = null;

        if (this.IsTrace)
            alert('init');

        this.item_clients_all = $("#item-clients-all");
        this.left_panel = $("#profile-clients-left");
        this.right_panel = $("#profile-clients-right");
        this.button_include = $("#profile-clients-include");
        this.button_exclude = $("#profile-clients-exclude");

        this.items = new Object();
        this.left_side = $("#profile-clients-left > ul");
        this.right_side = $("#profile-clients-right > ul");

        this.reset();
    },

    reset: function() {
        var self = this;

        if (this.IsTrace)
            alert('reset');

        this.right_side.children().each(function(index) {
            var item = $(this);
            var insert_before = self.getInsertBefore(item, $ProfileClients.left_side);

            if (insert_before != null)
                item.insertBefore(insert_before);
            else
                self.left.append(item);
        });

        self.items = new Object();
    },

    activate: function(checked)
    {
        if (this.IsTrace)
            alert('activate');

        if (checked) {
            this.left_panel.addClass('disabled');
            this.button_include.addClass('disabled');
            this.button_exclude.addClass('disabled');
            this.right_panel.addClass('disabled');
        } else {
            this.left_panel.removeClass('disabled');
            this.button_include.removeClass('disabled');
            this.button_exclude.removeClass('disabled');
            this.right_panel.removeClass('disabled');
        }

        this.item_clients_all.prop('checked', checked);
    },

    _get_item: function(id, container)
    {
        var item = null;

        container.children().each(function(index) {
            if (item != null)
                return;
            else if ($(this).attr('id').split(DEFAULT_HTML_SPLITTER)[1] == id) {
                item = $(this);
            }
        });

        return item;
    },

    getInsertBefore: function(item, container)
    {
        var data = item.attr('data').toLowerCase();
        var insert_before = null;

        if (this.IsTrace)
            alert(data);

        if (is_null(data) || data === undefined || data == '')
            return null;

        container.children().each(function(index) {
            if (insert_before != null)
                return;
            else if ($(this).attr('data').toLowerCase() > data) {
                insert_before = $(this);
            }
        });

        if (this.IsTrace)
            alert('--> before:'+(insert_before != null ? insert_before.attr('data') : '...'));

        return insert_before;
    },

    update: function(data)
    {
        if (is_null(data) || data === undefined || data == '')
            return;

        if (this.IsTrace)
            alert('update');

        var clients = data.split(DEFAULT_HTML_SPLITTER);

        for (var i=0; i < clients.length; i++) {
            var id = clients[i];
            var item = this._get_item(id, this.left_side);
            
            if (is_null(item))
                continue;

            var insert_before = this.getInsertBefore(item, this.right_side);

            if (insert_before != null)
                item.insertBefore(insert_before);
            else
                this.right_side.append(item);

            this.items[id] = 1;
        }

        this.item_clients_all.prop('checked', clients.length > 0 ? 0 : 1);
        this.activate(clients.length > 0 ? false : true);
    },

    setLeft: function(ob, force) {
        if (!force && this.selected_left_item != null)
            this.selected_left_item.removeClass('selected');
       
        ob.addClass('selected');
        this.selected_left_item = ob;
    },

    setRight: function(ob, force) {
        if (!force && this.selected_right_item != null)
            this.selected_right_item.removeClass('selected');
        
        ob.addClass('selected');
        this.selected_right_item = ob;
    },

    getItems: function() {
        var ids = new Array();
        for (var id in this.items) {
            if (this.items[id] == 1)
                ids[ids.length] = id;
        }
        return ids;
    },

    onAddClientProfileItem: function(ob) {
        var item = this.selected_left_item;
        var container = this.right_side;

        if (this.IsTrace)
            alert(left.prop('tagName')+':'+right.prop('tagName'));

        var insert_before = this.getInsertBefore(item, container);

        if (insert_before != null)
            item.insertBefore(insert_before);
        else
            container.append(item);

        item.removeClass('selected');

        var id = item.attr('id').split(DEFAULT_HTML_SPLITTER)[1];
        this.items[id] = 1;

        $setUserFormSubmit(0);

        this.selected_right_item = null;
        var ob = this.getInsertBefore(item, this.left_side);
        if (ob == null)
            return;

        this.setLeft(ob, true);
    },

    onRemoveClientProfileItem: function(ob) {
        var item = this.selected_right_item;
        var container = this.left_side;

        if (this.IsTrace)
            alert(left.prop('tagName')+':'+right.prop('tagName'));

        var insert_before = this.getInsertBefore(item, container);

        if (insert_before != null)
            item.insertBefore(insert_before);
        else
            container.append(item);

        item.removeClass('selected');

        var id = item.attr('id').split(DEFAULT_HTML_SPLITTER)[1];
        this.items[id] = 0;

        $setUserFormSubmit(0);

        this.selected_left_item = null;
        var ob = this.getInsertBefore(item, this.right_side);
        if (ob == null)
            return;

        this.setRight(ob, true);
    }
};

// =========================================================== //

function $setUserFormSubmit(disabled) {
    var container = $("#user-form");
    $("#save", container).prop("disabled", disabled);
}

function $cleanUserForm() {
    var container = $("#user-form");

    $("#login", container).val('').focus();
    $("#password", container).val('');
    $("#family_name", container).val('');
    $("#first_name", container).val('');
    $("#last_name", container).val('');
    $("#email", container).val('');

    var ob = $("#role", container);
    $("option", ob).each(function() {
        var id = $(this).attr('value');
        $(this).prop('selected', int(id) == 0 ? true : false);
    });

    $("#profile-name").html('');

    $("#confirmed", container).prop('checked', 1);
    $("#enabled", container).prop('checked', 1);

    $setUserFormSubmit(0);
}

function $updateUserForm(data) {
    var container = $("#user-form");

    if (is_null(data))
        return;

    $("#login", container).val(data.login);
    $("#password", container).val(data.password);
    $("#family_name", container).val(data.family_name);
    $("#first_name", container).val(data.first_name);
    $("#last_name", container).val(data.last_name);
    $("#email", container).val(data.email);

    var ob = $("#role", container);
    $("option", ob).each(function() {
        var id = $(this).attr('value');
        $(this).prop('selected', data.role == int(id) ? true : false);
    });

    $("#profile-name").html(data.family_name + ' ' + data.first_name + (data.last_name.length>0 ? ' '+data.last_name : ''));

    $("#confirmed", container).prop('checked', data.confirmed);
    $("#enabled", container).prop('checked', data.enabled);

    $setUserFormSubmit(1);
}

function $updateLog(data, props) {
    var container = null;

    function set_table(container, mode) {
        var no_data = '<tr><td><div class="nodata">'+keywords['No data']+'</div></td></tr>';
        var body = '<tr class="CLASS"><td class="name">NAME</td><td class="value">VALUE</td></tr>';
        var row = '';
        var n = 0;

        container.html('');

        if (mode == 1) {
            row = (
                '<div id="caption" style="display:none;">\n'+
                '<div class="c1">\n'+
                  '<h1 class="center">Производственное задание</h1>\n'+
                  '<h2 class="center">Тип партии: <span class="value">NAME</span></h2>\n'+
                  '<h2 class="center">Номер ТЗ: <span class="value">NUMBER</span>'+', кол-во: <span class="value">NO</span>'+'</h2>\n'+
                '</div>\n'+
                '<ul>\n'+
                  '<li class="title">Файл заказа: <span class="value">FILE</span></li>\n'+
                  '<li class="title">Кол-во записей в файле заказа: <span class="value">CARDS</span></li>\n'+
                '</ul>\n'+
                '</div>\n'
            )
                .replace(/NAME/g, props['name'])
                .replace(/NUMBER/g, props['number'])
                .replace(/NO/g, props['no'])
                .replace(/FILE/g, props['file'])
                .replace(/CARDS/g, props['cards']);
        }

        row += '<table class="view-data params" id="data_'+(mode==0 ? 'system' : 'user')+'_params" border="1"><thead class="header hidden"><tr>'+
                 '<td><span style="display:none;">Параметр</span></td>'+
                 '<td><span style="display:none;">Значение</span></td>'+
               '</tr></thead>';

        for(var i=0; i < data.length; i++) {
            if (!(data[i]['PType'] == mode || (mode == 0 && data[i]['PType'] < 0)))
                continue;

            var class_name = 'class_name' in data[i] ? data[i]['class_name'] : '';
            var name = data[i]['PName'];
            var value = data[i]['PValue'];
            
            row += body
                .replace(/CLASS/g, class_name)
                .replace(/NAME/g, name)
                .replace(/VALUE/g, value);

            ++n;
        }

        if (n == 0) row += no_data;

        row += '</table>';

        var barcode = 'barcode' in props ? props['barcode'] : '';

        if (barcode.length)
            row += '<div id="barcode" style="display:none;"><img class="barcode" src="data:image/png;base64,'+barcode+'"></div>';

        container.append(row);

        return n;
    }

    $ActivateInfoData(0);

    // --------------
    // Параметры TODO
    // --------------

    container = $("#EXTODO");

    function _check_todo(key) {
        var src = $SCRIPT_ROOT+'/static/img/';
        var image = '';
        var info = '';

        if (props[key]) {
            image = src + 'exclamation-40.png';
            info = keywords['Exclamation:'+key];
        }
        else {
            image = src + 'OK-40.png';
            info = keywords['OK:'+key];
        }

        return {'image':image, 'info':info};
    }

    if (container != null) {
        container.html('');

        var content = '';

        ['exists_inactive', 'exists_materials'].forEach(function(key) {
            if (key in props) {
                var x = _check_todo(key);
                content += 
                  '<tr>'+
                    '<td class="todo_image"><img src="'+x['image']+'"></td>'+
                    '<td class="todo_info"><span">'+x['info']+'</span></td>'+
                  '</tr>';
            }
        });

        if (!is_empty(content) && content.length > 0)
            content += 
                '<table class="view-data" id="data_todo" border="1">'+
                    content+
                '</table>';

        container.append(content);
    }

    var number = props['number'];
    var id = props['id'];

    if (is_empty(id))
        return;

    // --------------
    // Параметры DATA
    // --------------

    container = $("#EXDATA");

    if (!is_null(container)) {
        $("#ex_data").html(id);
        set_table(container, 0);
    }

    // --------------
    // Параметры FORM
    // --------------

    container = $("#EXFORM");

    function _enable_buttons(ob, enabled) {
        $("button", ob).each(function() {
            if (enabled)
                $(this).removeClass('disabled')
                    .attr('disabled', false)
                    .show(); //.css("display", "block");
            else
                $(this).addClass('disabled')
                    .attr('disabled', true)
                    .hide();
        });
    }

    if (container != null) {
        $("#ex_form").html(number);

        var enabled = set_table(container, 1) > 0 ? true : false;

        _enable_buttons($("#ex_form_buttons"), enabled);
        _enable_buttons($("#admin_form_buttons"), enabled);
    }

    $ActivateInfoData(1);

    // ----------------
    // Run Page Handler
    // ----------------

    if (typeof log_callback === 'function')
        log_callback(data, props);
}

function $updateLogPagination(pages, rows, iter_pages, has_next, has_prev, per_page) {
}

function $updateTabData(action, data, columns, total) {
    var flash = $("#flash-section");
    var mid = '';

    //alert(action+':'+data.length.toString()+':'+total);

    function set_text(container, title) {
        var no_data = '<div class="nodata">'+keywords['No data']+'</div>';
        var parent = container.parent();

        $(".row-counting", parent).remove();

        if (data.length == 0) {
            container.html(no_data);
            container.addClass('p50');
        } else {
            container.text(data);
            container.parent().append(
                '<div class="row-counting">'+(title || 'Всего записей')+': '+total.toString()+'</div>'
                );
            container.removeClass('p50');
        }
    }

    function set_table(container, class_name, template) {
        var header = '<td class="column header">VALUE</td>'; // nowrap
        var row = '<tr class="CLASS-LOOP-SELECTED"ID>LINE</tr>';
        var column = '<td class="CLASS-ERROR-READY-SELECTED"EXT>VALUE</td>';
        var no_data = '<tr><tdEXT><div class="'+
                (['306','307','308'].indexOf(action) > -1 ? 
                    'nodataoraccess">'+keywords['No data or access denied'] : 
                    'nodata">'+keywords['No data'])+
            '</div></td></tr>';
        var content = '';
        var filename = '';

        container.html('');

        content += template || '<table class="view-data" id="tab-view-content" border="1"><thead><tr>';

        for(var i=0; i < columns.length; i++) {
            content += header
                .replace(/VALUE/g, columns[i]['header']);
        }

        content += '</tr></thead>';

        if (data.length == 0) {
            content += no_data
                .replace(/EXT/g, ' colspan="'+columns.length.toString()+'"');
        } else {
            for(var i=0; i < data.length; i++) {
                var line = '';
                var ob = data[i];

                if ('exception' in ob && !is_null(flash)) {
                    flash.append('<div class="flash">'+ob['exception']+'</div>');
                    continue;
                }

                var error = ('Error' in ob && ob['Error']) ? ' error' : '';
                var ready = ('Ready' in ob && ob['Ready']) ? ' ready' : '';
                var selected = ob['selected'] ? ' '+ob['selected'] : '';
                var id = ('id' in ob && ob['id']) ? ' id="row-'+(class_name || 'tabline')+':'+ob['id']+':'+(i+1).toString()+'"' : '';

                if ('filename' in ob && filename != ob['filename']) {
                    filename = ob['filename'];
                    line = column
                        .replace(/CLASS-ERROR-READY-SELECTED/g, '')
                        .replace(/VALUE/g, filename)
                        .replace(/EXT/g, ' colspan="'+columns.length.toString()+'"');

                    content += row
                        .replace(/CLASS-LOOP-SELECTED/g, 'log-header')
                        .replace(/ID/g, '')
                        .replace(/LINE/g, line);

                    line = '';
                }

                for(var j=0; j < columns.length; j++) {
                    var name = columns[j]['name'];
                    var value = (name.length > 0 && (name in ob)) ? ob[name].toString() : '';

                    line += column
                        .replace(/CLASS/g, 'column log-'+(name == 'Code' && value.length > 0 ? value.toLowerCase() : name.toLowerCase()))
                        .replace(/-ERROR/g, error)
                        .replace(/-READY/g, ready)
                        .replace(/-SELECTED/g, selected)
                        .replace(/EXT/g, '')
                        .replace(/VALUE/g, value);
                }

                content += row
                    .replace(/ID/g, id)
                    .replace(/CLASS/g, class_name || 'tabline')
                    .replace(/-LOOP/g, ' '+(i%2==0 ? 'even' : 'odd'))
                    .replace(/-SELECTED/g, selected)
                    .replace(/LINE/g, line);
            }
        }

        content += '</table>';

        content += '<div class="row-counting">Всего записей: '+data.length.toString()+'</div>';

        //alert(container.attr('id')+':'+content);

        container.append(content);
    }

    switch (action) {
        case '300':
            set_table($("#MAINDATA"), 'subline', '<table class="view-data p100" border="1"><thead><tr>');
            mid = 'data-menu-batches';
            break;
        
        case '302':
            set_table($("#logs-container"));
            mid = 'data-menu-logs';
            break;
        
        case '303':
            set_table($("#cardholders-container"));
            mid = 'data-menu-cardholders';
            break;
        
        case '304':
            set_text($("#ibody-container"), 'Общая длина контента');
            mid = 'data-menu-body';
            break;
        
        case '305':
            set_text($("#processerrmsg-container"), 'Всего записей (ошибок)');
            mid = 'data-menu-processerrmsg';
            break;
        
        case '306':
            set_table($("#persolog-container"));
            mid = 'data-menu-persolog';
            break;
        
        case '307':
            set_table($("#sdclog-container"));
            mid = 'data-menu-sdclog';
            break;
        
        case '308':
            set_table($("#exchangelog-container"));
            mid = 'data-menu-exchangelog';
            break;
        
        case '401':
            set_table($("#preloadlog-container"));
            mid = 'data-menu-preloadlog';
            break;

        case '500':
            set_table($("#MAINDATA"), 'subline', '<table class="view-data p100" border="1"><thead><tr>');
            mid = 'data-menu-events';
            break;
        
        case '502':
            set_table($("#files-container"));
            mid = 'data-menu-files';
            break;
        
        case '503':
            set_table($("#errors-container"));
            mid = 'data-menu-errors';
            break;
        
        case '504':
            set_table($("#certificates-container"));
            mid = 'data-menu-certificates';
            break;
        
        case '505':
            set_table($("#aliases-container"));
            mid = 'data-menu-aliases';
            break;
        
        case '506':
            set_table($("#log-container"));
            mid = 'data-menu-log';
            break;

        case '600':
            set_table($("#MAINDATA"), 'subline', '<table class="view-data p100" border="1"><thead><tr>');
            mid = 'data-menu-batches';
            break;

        case '602':
            set_table($("#processes-container"));
            mid = 'data-menu-processes';
            break;

        case '603':
            set_table($("#opers-container"));
            mid = 'data-menu-opers';
            break;

        case '604':
            set_table($("#operparams-container"));
            mid = 'data-menu-operparams';
            break;

        case '605':
            set_table($("#filters-container"));
            mid = 'data-menu-filters';
            break;

        case '606':
            set_table($("#tags-container"));
            mid = 'data-menu-tags';
            break;

        case '607':
            set_table($("#tagvalues-container"));
            mid = 'data-menu-tagvalues';
            break;

        case '608':
            set_table($("#tzs-container"));
            mid = 'data-menu-tzs';
            break;

        case '609':
            set_table($("#erpcodes-container"));
            mid = 'data-menu-erpcodes';
            break;

        case '610':
            set_table($("#materials-container"));
            mid = 'data-menu-materials';
            break;

        case '611':
            set_table($("#posts-container"));
            mid = 'data-menu-posts';
            break;

        case '612':
            set_table($("#processparams-container"));
            mid = 'data-menu-processparams';
            break;

        case '700':
            set_table($("#MAINDATA"), 'subline', '<table class="view-data p100" border="1"><thead><tr>');
            mid = 'data-menu-opers';
            break;
        
        case '702':
            set_table($("#logs-container"));
            mid = 'data-menu-logs';
            break;
        
        case '703':
            set_table($("#units-container"));
            mid = 'data-menu-units';
            break;
        
        case '704':
            set_table($("#params-container"));
            mid = 'data-menu-params';
            break;
    }
    
    if (mid.length > 0) 
        $ShowMenu(mid);

    if (action != default_action)
        selected_menu_action = action;
}

function $updateSublineData(action, response, props, total) {
    var currentfile = response['currentfile'];
    var sublines = response['sublines'];
    var config = response['config'];
    var filename = currentfile[1];

    $(".filename").each(function() { 
        $(this).html(filename);
    });

    if (default_submit_mode != 0)
        $updateTabData(action, sublines, config, total);

    $SublineSelector.init();

    var data = response['data'];
    var columns = response['columns'];

    selected_menu_action = response['action'];

    if (selected_menu_action == default_log_action)
        $updateLog(data, props);
    else
        $updateTabData(selected_menu_action, data, columns, total);
}
