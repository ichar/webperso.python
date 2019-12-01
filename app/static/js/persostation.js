// *************************************************
// PERSOSTATION PAGE DECLARATION: /persostation.html
// -------------------------------------------------
// Version: 1.00
// Date: 26-11-2018

default_submit_mode = 2;
default_action      = '800';
default_log_action  = '801';
default_input_name  = 'order_id';
default_menu_item   = 'data-menu-batches';

LINE    = 'order';
SUBLINE = 'batch';

// ----------------------
// Dialog Action Handlers
// ----------------------

function sidebar_callback() {
    $onInfoContainerChanged();
}

function subline_refresh(filename) {
    $(".filename").each(function() { 
        $(this).html(filename);
    });
}

function log_callback(current_action, data, props) {
}

// --------------
// Page Functions
// --------------

IsTrace = 0;

function $Init() {
    $SidebarControl.init(sidebar_callback);

    page_sort_title = $("#sort_icon").attr('title');

    SelectedReset();

    $LineSelector.init();
    $SublineSelector.init();

    $ShowMenu('data-menu-batches');

    $TabSelector.init();

    // ------------------------
    // Start default log action
    // ------------------------

    interrupt(true, 1);
}


function $ShowMenu(id) {

    // -----------------------------------------
    // Show (open) selected DataMenu item (Tabs)
    // -----------------------------------------

    var batches = $("#subline-content");
    var tab = $("#"+id);

    if (selected_data_menu)
        selected_data_menu.removeClass('selected');

    selected_data_menu = tab;

    batches.hide();

    if (id == 'data-menu-batches')
        batches.show();

    if (id == default_menu_item)
        $SublineSelector.init();
    else
        $TablineSelector.init(tab);

    if (id == default_menu_item && SelectedGetItem(SUBLINE, 'id'))
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
    var id = ob.attr("id");
    var action = null;

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
        //  1 - changed batchtype
        //  2 - changed date from
        //  3 - changed date to
        //  4 - changed operator

        case 0:
            $("#batchtype").each(function() { $(this).val(0); });
            $("#operator").each(function() { $(this).val(''); });
        case 1:
            $("#operator").each(function() { $(this).val(''); });
        case 2:
        case 3:
        case 4:
        case 5:
            break;

        // ---------------------------
        // LineSelector Handler submit
        // ---------------------------

        case 9:
            $("#order_id").each(function() { $(this).val(0); });
            $("#batch_id").each(function() { $(this).val(0); });
            $("#batchtype").each(function() { $(this).val(0); });
            $("#operator").each(function() { $(this).val(''); });
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
    // ---------------
    // Register's Form
    // ---------------

    function $onPersostationSubmit(id) {
        var frm = $("#persostation");
        $("#active", frm).val(id);
        frm.submit();
    }

    $("input", "#persostation").on('change', function(e) { //  keyup paste
    	var id = $(this).attr('id');
        $onPersostationSubmit(id);
    });

    $("select").on('change', function(e) {
        var id = $(this).attr('id');
        if (id != 'batches') $onPersostationSubmit(id);
    });

    $("#batches").on('click', function(e) {
        var id = $(this).val();
        var value = $("#batches option:selected").text();
        var active = value.indexOf(operator) > -1 ? true : false;
        var other = (!active && value.split('=').length > 2) ? true : false;
    	var box = $("#buttons");
    	var disabled = 'disabled';
        if (box.hasClass(disabled)) box.removeClass(disabled);
        /*
        if (OKDisabled) $("#ok").attr(disabled, OKDisabled);
        if (CancelDisabled) $("#cancel").attr(disabled, CancelDisabled);
        */
        $("#ok").prop(disabled, active || other ? true : false);
        $("#cancel").prop(disabled, other || !active ? true : false);
    });

    // --------------
    // Line selection
    // --------------

    $(".line").click(function(e) {
        if (is_show_error)
            return;

        $LineSelector.onRefresh($(this));
    });

    // -----------------
    // SubLine selection
    // -----------------

    $("#subline-content").on('click', '.subline', function(e) {
        if (is_show_error)
            return;

        $SublineSelector.onRefresh($(this));
    });

    // ---------------------
    // Data Section progress
    // ---------------------

    $("#data-section").on('click', '.column', function(e) {
        var ob = $(this);
        var parent = ob.parents("*[class*='line']").first();
        if (!is_null(parent) && !parent.hasClass("tabline") && !ob.hasClass("header"))
            $InProgress(ob, 1);
    });

    // -------------
    // Resize window
    // -------------

    $(window).on("resize", function() {
        resize();
    });

    $(window).scroll(function(e){});

    // --------
    // Keyboard
    // --------

    $(window).keydown(function(e) {
        if ($ConfirmDialog.is_focused() || $NotificationDialog.is_focused())
            return;

        if (is_show_error)
            return;

        if (e.keyCode==13) {                                     // Enter
        }

        if (is_search_focused)
            return;

        var exit = false;

        //alert(e.ctrlKey+':'+e.shiftKey+':'+e.altKey+':'+e.keyCode);

        if (exit) {
            e.preventDefault();
            return false;
        }
    });
});

function page_is_focused(e) {
    return false;
}

function resize() {
    var ob = $("#client");
    var top = getattr(ob.position(), 'top', 0);
    var left = getattr(ob.position(), 'left', 0);
    if (!is_null(left)) $("#trigger").css('top', top-45).css('left', left+400);
}

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (persostation)');

    current_context = 'persostation';
    resize();

    try {
        $_init();
    }
    catch(e) {}
});
