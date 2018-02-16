// *************************************************
// CONFIGURATOR PAGE DECLARATION: /configurator.html
// -------------------------------------------------
// Version: 1.40
// Date: 05-09-2017

default_submit_mode = 2;
default_action      = '600';
default_log_action  = '601';
default_input_name  = 'file_id';

LINE    = 'file';
SUBLINE = 'batch';

// ----------------------
// Dialog Action Handlers
// ----------------------

function $_reset_current_sort() {
    current_page = 1;
}

function $_next_current_sort() {
    current_sort = current_sort == LOG_SORT.length-1 ? 0 : current_sort + 1;
    $_reset_current_sort();
}

function $_deactivate_search() {
    is_search_activated = false;
    search_context = '';
    current_page = 1;
}

function $_reset_item() {
    refresh_current_state = true;
    SelectedReset();
}

function $_reset_page() {
    SelectedReset();
    current_row_id = null;
}

function $_calculating_disabled() {
    return false;
}

// --------------
// Page Functions
// --------------

function sidebar_callback() {
    $onInfoContainerChanged();
}

function $Init() {
    $SidebarControl.init(sidebar_callback);

    page_sort_title = $("#sort_icon").attr('title');

    SelectedReset();

    $LineSelector.init();

    var parent = $("#line-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(LINE, ob, 'add', null);

    $LineSelector.set_current(ob);

    $SublineSelector.init();

    var parent = $("#subline-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(SUBLINE, ob, 'add', null);

    $SublineSelector.set_current(ob);

    $ShowMenu('data-menu-batches');

    $TabSelector.init();

    // ------------------------
    // Start default log action
    // ------------------------

    interrupt(true, 1);
}

function $ActivateInfoData(show) {
    var container = $("#info-data");

    if (show)
        container
            .show();
    else {
        container.hide();
        return;
    }

    $PageScroller.reset(true);
}

function $Confirm(mode, ob) {
    $ConfirmDialog.close();
}

function $Notification(mode, ob) {
    $NotificationDialog.close();
}

function $ShowMenu(id) {
    //
    // Show (open) selected DataMenu item (Tabs)
    //
    var batches = $("#subline-content");
    var processes = $("#processes-content");
    var opers = $("#opers-content");
    var operparams = $("#operparams-content");
    var filters = $("#filters-content");
    var tags = $("#tags-content");
    var tagvalues = $("#tagvalues-content");
    var tzs = $("#tzs-content");
    var erpcodes = $("#erpcodes-content");
    var materials = $("#materials-content");
    var posts = $("#posts-content");
    var processparams = $("#processparams-content");

    if (selected_data_menu)
        selected_data_menu.removeClass('selected');

    selected_data_menu = $("#"+id);
    //$("#data-content").scrollTop(0);

    batches.hide();
    processes.hide();
    opers.hide();
    operparams.hide();
    filters.hide();
    tags.hide();
    tagvalues.hide();
    tzs.hide();
    erpcodes.hide();
    materials.hide();
    posts.hide();
    processparams.hide();

    if (id == 'data-menu-batches')
        batches.show();
    else if (id == 'data-menu-processes')
        processes.show();
    else if (id == 'data-menu-opers')
        opers.show();
    else if (id == 'data-menu-operparams')
        operparams.show();
    else if (id == 'data-menu-filters')
        filters.show();
    else if (id == 'data-menu-tags')
        tags.show();
    else if (id == 'data-menu-tagvalues')
        tagvalues.show();
    else if (id == 'data-menu-tzs')
        tzs.show();
    else if (id == 'data-menu-erpcodes')
        erpcodes.show();
    else if (id == 'data-menu-materials')
        materials.show();
    else if (id == 'data-menu-posts')
        posts.show();
    else if (id == 'data-menu-processparams')
        processparams.show();

    if (id == 'data-menu-batches' && SelectedGetItem(SUBLINE, 'id'))
        $ActivateInfoData(1);
    else
        $ActivateInfoData(0);

    selected_data_menu.addClass('selected');
    selected_data_menu_id = id;
}

function $onPaginationFormSubmit(frm) {
    return true;
}

function $onFilterFormSubmit(frm) {
    return true;
}

function $onInfoContainerChanged() {
    //alert($_width('screen-min')-$("#sidebarFrame").width()+':'+$("#line-table").width());
}

function $onTabSelect(ob) {
    var id = ob.attr('id');
    var action = 
        id == 'data-menu-processes' ? '602' : (
        id == 'data-menu-opers' ? '603' : (
        id == 'data-menu-operparams' ? '604' : (
        id == 'data-menu-filters' ? '605' : (
        id == 'data-menu-tags' ? '606' : (
        id == 'data-menu-tagvalues' ? '607' : (
        id == 'data-menu-tzs' ? '608' : (
        id == 'data-menu-erpcodes' ? '609' : (
        id == 'data-menu-materials' ? '610' : (
        id == 'data-menu-posts' ? '611' : (
        id == 'data-menu-processparams' ? '612' : null
        ))))))))));

    selected_menu_action = action;

    if (action != null) {
        $InProgress(ob, 1);
        $Go(action);
    }
    else if (default_submit_mode > 1) {
        selected_menu_action = default_log_action;
        $InProgress(ob, 1);
        $Go(default_action);
    }
    else
        $ShowMenu(id);

    return true;
}

// ===========================
// Dialog windows declarations
// ===========================

function MakeFilterSubmit(mode, page) {
    $("#filter-form").attr("action", baseURI);

    switch (mode) {

        // -------------
        // Submit modes:
        // -------------
        //  0 - changed client
        //  1 - changed file type
        //  2 - changed batch type
        //  3 - changed tag
        //  4 - changed tag value

        case 0:
            $("#batch_id").each(function() { $(this).val(0); });
            $("#filetype").val(0);
        case 1:
            $("#batchtype").val(0);
        case 2:
            $("#tag").val(0);
        case 3:
            $("#tagvalue").val(0);
        case 4:
            break;

        // ---------------------------
        // LineSelector Handler submit
        // ---------------------------

        case 9:
            $("#file_id").each(function() { $(this).val(0); });
            $("#batch_id").each(function() { $(this).val(0); });
    }

    $ResetLogPage();
    $setPaginationFormSubmit(page);
    $onParentFormSubmit('filter-form');
}

// ====================
// Page Event Listeners
// ====================

jQuery(function($) 
{
    // --------------
    // Line selection
    // --------------

    $(".line").click(function(e) {
        var ob = $(this);
        $LineSelector.set_current(ob);
        $onToggleSelectedClass(LINE, ob, 'submit', null);
    });

    // -----------------
    // SubLine selection
    // -----------------

    $("#subline-content").on('click', '.subline', function(e) {
        var ob = $(this);
        $SublineSelector.onRefresh(ob);
    });

    // ---------------------
    // Data Section progress
    // ---------------------

    $("#data-section").on('click', '.column', function(e) {
        var ob = $(this);
        var parent = ob.parents("*[class*='line']").first();
        if (!is_null(parent) && !parent.hasClass("tabline"))
            $InProgress(ob, 1);
    });

    // ------------------------------
    // Tab table lines data selection
    // ------------------------------

    $(".view-lines").on('click', '.tabline', function(e) {
        var ob = $(this);

        if (!is_null(current_tabline))
            $onToggleSelectedClass(TABLINE, current_tabline, 'remove', null);
        
        current_tabline = ob;
        SelectedSetItem(TABLINE, 'ob', current_tabline);

        $onToggleSelectedClass(TABLINE, current_tabline, 'add', null);
    });

    // ------------------------
    // Control Panel Menu items
    // ------------------------

    $("#reference-container").on('click', '.reference-item', function(e) {
        $ReferenceDialog.toggle($(this));
    });

    $("#reference-container").on('click', '.reference-icon', function(e) {
        $ReferenceDialog.onIconClick($(this));
    });

    $("button[id^='admin']", this).click(function(e) {
        var ob = $(this);
        var command = ob.attr('id');

        $onControlPanelClick($("#admin-panel-dropdown"));

        if (['admin:xxxxxxx'].indexOf(command) > -1) {
            return;
        }

        $onToggleSelectedClass(LINE, null, 'submit', command, true);
    });

    $("button[id^='service']", this).click(function(e) {
        var ob = $(this);
        var command = ob.attr('id');
        var reference = command.split(':')[1];

        $onControlPanelClick($("#services-dropdown"));
        
        if (['clients','file-status','batch-status','oper-list','tag-params'].indexOf(reference) > -1) {
            $ReferenceDialog.confirmation(command);
            return;
        }
    });

    $("button[id^='action']", this).click(function(e) {
        var ob = $(this);
        var command = ob.attr('id');

        $onControlPanelClick($("#actions-dropdown"));
        
        if (command == 'action:xxxxxxxxxx') {
            return;
        }

        $("#command").val(command);
        $onParentFormSubmit('filter-form');
        e.preventDefault();
    });

    // --------------
    // Tabs Data menu
    // --------------

    $("div[id^='data-menu']", this).click(function(e) {
        $TabSelector.onClick($(this));
    });

    // --------
    // Keyboard
    // --------

    $(window).keydown(function(e) {
        if ($ConfirmDialog.is_focused() || $NotificationDialog.is_focused())
            return;

        var exit = false;

        // REFERENCE DEBUG

        if (e.shiftKey && e.keyCode==113)       // F2
            $ReferenceDialog.confirmation('service:clients');

        else if (e.shiftKey && e.keyCode==114)  // F3
            $ReferenceDialog.confirmation('service:oper-list');

        else if (e.shiftKey && e.keyCode==115)  // F4
            $ReferenceDialog.confirmation('service:tag-params');

        if (exit) {
            e.preventDefault();
            return false;
        }
    });
});

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (configurator)');

    $("#search-context").attr('placeholder', 'Найти (тип файла)...');
    //$("#header-section").css('height', 210);
    //$("#menu").css('height', $("#log-filter").height()+20);

    $_init();
});
