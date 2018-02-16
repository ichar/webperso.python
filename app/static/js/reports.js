// ****************************
// PRINTABLE FORMS: /reports.js
// ----------------------------
// Version: 1.00
// Date: 22-11-2017

var report_body = '';

function printBankpersoTZ(div) {

    var show = 0;

    makePageLandscape(show);
    makeStyles('bankperso', 'TZ');

    makeBankperso_TZ(div);

    printReport(show);
}

function printBankpersoMaterials(data, props) {

    var show = props['show'];

    makePageLandscape(show);
    makeStyles('bankperso', 'materials');

    makeBankperso_Materials(data, props);

    printReport(show);
}

function printBankpersoContainerList(data, props) {

    var show = props['show'];

    makePagePortrait(show);
    makeStyles('bankperso', 'containerlist');

    makeBankperso_ContainerList(data, props);

    printReport(show);

}

function printCardsPacket(data, props) {
    // https://stackoverflow.com/questions/138422/landscape-printing-from-html
    // https://stackoverflow.com/questions/39025840/change-window-print-paper-orientation

    var show = props['show'];

    makePageLandscape(show);
    makeStyles('cards', 'all');

    makeCardsReport_1(data, props, 0, 0);

    printReport(show);

    // ===========

    makePagePortrait(show);
    makeStyles('cards', 'r35');

    var page_break = 0;
    var is_print = false;
    
    if (props['has_mir']) {
        makeCardsReport_3(props, 0, 1);
        page_break = 1;
        is_print = true;
    }

    if (props['has_protocol']) {
        makeCardsReport_5(props, page_break, 1);
        is_print = true;
    }

    if (is_print)
        printReport(show);

    // ===========

    makePageLandscape(show);
    makeStyles('cards', 'all');

    makeCardsReport_2(props, 0);

    if (props['blanks'].length > 0)
        makeCardsReport_4(props, 1);

    printReport(show);
}

function printCardsSelectedReport(data, props, report) {
    if (is_empty(report))
        return;

    var show = props['show'];

    if (['r1','r2','r4'].indexOf(report) > -1)
        makePageLandscape(show);
    else
        makePagePortrait(show);

    makeStyles('cards', report);

    switch (report) {
        case 'r1':
            makeCardsReport_1(data, props, 0, 0);
            break;
        case 'r2':
            makeCardsReport_2(props, 0);
            break;
        case 'r3':
            makeCardsReport_3(props, 0, 1);
            break;
        case 'r4':
            if (props['blanks'].length > 0)
                makeCardsReport_4(props, 0);
            else {
                $ShowError(keywords['Warning:No report data'], true, true, false);
                return;
            }
            break;
        case 'r5':
            makeCardsReport_5(props, 0, 1);
            break;
    }

    printReport(show);
}

function hide_screen(body, show) {

    report_body = body
        .replace(/HIDE_SCREEN/g, 
            (show && (isOpera || isChrome)) ? '' : '<style type="text/css" media="screen">body { display:none; }</style>');

}

function makePageLandscape(show) {

    var body =
        //'<!DOCTYPE html>\n'+
        //'<html lang="ru"><head><meta charset="UTF-8"><title></title>\n'+
        '<html><head><title></title>\n'+
        'HIDE_SCREEN\n'+
        '<style type="text/css" media="screen,print">\n'+
        '@page { size:landscape; width:300mm; height:170mm; }\n'+
        'body { margin:10px 20px 10px 20px; font-family:Arial,Tahoma; background-color:#ffffff; }\n'+
        '.page { margin:0px auto; padding:0; overflow:hidden; }\n'+
        //'.landscape { width:276mm; height:190mm; }\n'+
        //'.landscape { transform:rotate(270deg) translate(-276mm, 0); transform-origin:0 0; filter:progid:DXImageTransform.Microsoft.BasicImage(rotation=3); }\n'+
        //'.landscape { -webkit-transform: rotate(270deg); -moz-transform:rotate(270deg); filter:progid:DXImageTransform.Microsoft.BasicImage(rotation=3); }\n'+
        '';

    hide_screen(body, show);

}

function makePagePortrait(show) {

    var body =
        //'<!DOCTYPE html>\n'+
        //'<html lang="ru"><head><meta charset="UTF-8"><title></title>\n'+
        '<html><head><title></title>\n'+
        'HIDE_SCREEN\n'+
        '<style type="text/css" media="screen,print">\n'+
        '@page { size:portrait; width:170mm; height:276mm; }\n'+
        'body { margin:10px 0 10px 0; font-family:Arial,Tahoma; background-color:#ffffff; }\n'+
        '.page { margin:0 auto; padding:0; overflow:hidden; }\n'+
        //'.portrait { width:210mm; page-break-after:auto; margin:0 auto; }\n'+
        //'.portrait { transform:rotate(90deg) translate(-276mm, 0); transform-origin:0 0; filter:progid:DXImageTransform.Microsoft.BasicImage(rotation=1); }\n'+
        '';

    hide_screen(body, show);

}

function makeStyles(module, report) {

    var title = 'WebPerso Doc Printer';

    report_body += 
        //'<html><head><title></title>\n'+
        //'<style type="text/css" media="screen,print">\n'+
        //'@page { size:landscape; width:276mm; height:170mm; }\n'+
        //'@page { size:portrait; }\n'+
        '.page-break { page-break-before:always; }\n'+
        'h1, h2 { font-weight:bold; margin:0; }\n'+
        'h1 { font-size:20px; }\n'+
        'h2 { font-size:16px; }\n'+
        'h3 { font-size:14px; }\n'+
        'h4 { font-size:12px; }\n';

    if (module == 'cards')
    {
        report_body += 

        'table.data { border-collapse:collapse; border-spacing:0px; border:1px solid #333; font-size:12px; width:100%; }\n'+
        'table.data td { padding:5px 10px 5px 10px; border:1px solid #777; }\n'+
        '.caption { font-weight:bold; font-size:14px; margin:10px auto; }\n'+
        '.caption span { padding:0 10px 0 10px; margin-left:5px; }\n'+
        '.high { font-size:22px; margin-top: -10px; }\n'+
        '.filename { font-size:18px; margin-top: -5px; }\n'+
        '.title { font-weight:bold; font-size:14px; white-space:nowrap; padding:5px 10px 5px 10px; }\n'+
        '.title span { padding:0 10px 0 10px; margin-left:5px; }\n'+
        '.keyword { font-weight:bold; font-size:14px; white-space:nowrap; }\n'+
        '.total { font-weight:bold; font-size:14px; margin-left:-1px; }\n'+
        '.inline div { display:inline-flex; }\n'+
        '.nowrap { white-space:nowrap; }\n'+
        '.underline { text-decoration:underline; }\n'+
        '.sharping { padding-bottom:2px; border-bottom:2px solid black; }\n'+
        '.bold { font-weight:bold !important; }\n'+
        '.center { text-align:center; }\n'+
        '.left { text-align:left; }\n'+
        '.right { float:right; text-align:right; clear:both; }\n'+
        '.p50 { width:50%; }\n'+
        '.header { font-weight:bold; text-align:left; }\n'+
        '.footer { font-weight:bold; font-size:12px; line-height:30px; white-space:nowrap; margin-top:20px; margin:10px auto; width:100%; }\n'+
        '.footer td { margin-left:10px; }\n'+
        '.sign { padding-left:10px; width:100px; border-bottom:0px solid black; }\n'+
        '.final { margin:20px 40px 20px 40px; }\n';
    }

    if (module == 'cards' && ['all','r1'].indexOf(report) > -1)
    {
        report_body += 

        '.r1_now { font-size:16px; margin:-10px 10px 0 10px; padding:3px 10px 3px 10px; }\n'+
        '.r1 td.np { text-align:center; }\n'+
        '.r1 td.sumqty { text-align:center; font-weight:bold; }\n'+
        '.r1 div.title, .r1 div.readydate { padding-bottom:10px; }\n'+
        'span.readydate { min-width:210px; }\n';
    }

    if (module == 'cards' && ['all','r2'].indexOf(report) > -1)
    {
        report_body += 

        '.r2 h1 { padding-left:60px; font-size:22px; margin-bottom:10px; white-space:nowrap; }\n'+
        '.r2 h3.sharping { padding-bottom:4px !important; border-bottom:1px solid black !important; line-height:12px; }\n'+
        '.r2_box { background-color:#aaa; padding:10px 20px 10px 20px; text-align:center; }\n'+
        '.r2_box td { padding:6px 10px 6px 10px; font-weight:normal; }\n'+
        '.r2_data, .r2_sign { width:100%; }\n'+
        '.r2_box td.title { background-color:#ffffff; font-weight:normal; border:2px solid #777; }\n'+
        '.r2_data tr.data td { font-weight:bold; font-size:14px; }\n'+
        '.r2_sign td { white-space:nowrap; font-size:12px; background-color:#ffffff; }\n'+
        '.r2_now { margin-bottom:10px; padding:5px 10px 3px 10px; border:1px solid #333; white-space:nowrap; }\n'+
        '.r2_footer { margin-left:20px; margin-right:20px; }\n';
    }

    if (module == 'cards' && ['all','r3','r35'].indexOf(report) > -1)
    {
        report_body += 

        // ------------------------
        // Single page for report 3
        // ------------------------

        '.r3 td { font-size:6px; }\n'+
        '.r3 h1 { font-size:16px; line-heigh:20px; }\n'+
        '.r3_box { padding:0px 10px 0px 10px; }\n'+
        '.r3 h2>span.caption { line-height:28px; padding:0px; border-bottom:2px solid black; font-size:12px; }\n'+
        '.r3_data, .r3_sign { width:100%; }\n'+
        '.r3_data { border-collapse:collapse; border-spacing:0px; border:0px solid #333; width:100%; }\n'+
        '.r3_data td { padding:0 3px 0 3px; border:1px solid #333; font-size:9px; }\n'+
        '.r3_data td.header { background-color:#ffffff; font-size:8px; border-bottom:4px double #777; padding:3px; }\n'+
        '.r3_data td.col5 { font-size:6px !important; font-weight:normal !important; }\n'+
        '.r3_data td.high { background-color:#e7e7e7; }\n';
    }

    if (module == 'cards' && ['all','r4'].indexOf(report) > -1)
    {
        report_body += 

        '.r4 td { font-size:12px; }\n'+
        '.r4 h1 { font-size:18px; }\n'+
        '.r4 h2 { font-size:16px; padding:2px; }\n'+
        '.r4 table.data { margin-top:10px; width:100%; }\n'+
        '.r4 td.header { font-size:14px; padding:5px 10px 5px 10px; }\n'+
        '.r4 td.col0 { width:120px; }\n'+
        '.r4 td.col1 { width:80px; }\n'+

        '';
    }

    if (module == 'cards' && ['all','r3','r5','r35'].indexOf(report) > -1)
    {
        report_body += 

        '.r35_sign { margin-top:2px; }\n'+
        '.r35_sign h4 { padding-top:0px; margin:0; }\n';
    }

    if (module == 'cards' && ['all','r5','r35'].indexOf(report) > -1)
    {
        report_body += 

        // ------------------------
        // Single page for report 5
        // ------------------------

        '.r5 td { font-size:6px; }\n'+
        '.r5 h1 { font-size:16px; line-heigh:20px; }\n'+
        '.r5_box { padding:0px 10px 0px 10px; }\n'+
        '.r5 h2>span.caption { line-height:28px; padding:0px; border-bottom:2px solid black; font-size:12px; }\n'+
        '.r5_data, .r5_sign { width:100%; }\n'+
        '.r5_data { border-collapse:collapse; border-spacing:0px; border:0px solid #333; width:100%; }\n'+
        '.r5_data td { padding:3px; border:1px solid #333; font-size:9px; }\n'+
        '.r5_data tr.header>td { background-color:#ffffff; font-size:9px; border-bottom:4px double #777; }\n'+
        '.r5_data tr.header>td.col3 { text-align:center; }\n'+
        '.r5_data tr.header>td.col4 { text-align:center; }\n'+
        '.r5_data tr.header>td.col5 { text-align:center; }\n'+
        '.r5_data tr.header>td.col6 { text-align:center; }\n'+
        '.r5_data tr.header>td.col7 { text-align:center; }\n'+
        '.r5_data td.col3 { text-align:center; }\n'+
        '.r5_data td.col4 { text-align:center; }\n'+
        '.r5_data td.high { background-color:#e7e7e7; }\n';
    }

    if (module == 'bankperso') 
    {
        report_body += 

        'h1 { font-size:20px; }\n'+
        '#caption { margin-top:0px; }\n'+
        '#caption h1 { font-size:24px; padding:10px; }\n'+
        '#caption h2 { padding:5px; }\n'+
        '.center { text-align:center; }\n'+
        '.nowrap { white-space:nowrap; }\n'+
        '.left { text-align:left; }\n'+
        '.right { text-align:right; }\n';
    }

    if (module == 'bankperso' && report == 'TZ') 
    {
        report_body += 

        '.content { font-size:14px; }\n'+
        '.c1 { margin-bottom:40px; }\n'+
        'table.params { border-collapse:collapse; border-spacing:0px; border:2px double #333; font-size:inherit; martin-top:10px; width:100%; }\n'+
        '.params td { padding:5px 10px 5px 10px; border:1px solid #ccc; width:50%; }\n'+
        '.params td.name { color:#333; }\n'+
        '.params td.value { font-weight:bold; color:#237; }\n'+
        '.params .header td { background-color:#eee; font-weight:bold; border-bottom:1px solid #333; padding:10px; text-align:center; font-size:16px; }\n'+
        'ul { margin-top:20px; }\n'+
        'li { list-style-type:none; font-weight:bold; padding-bottom:10px; }\n'+
        'span.value { font-weight:bold; margin-left:5px; }\n'+
        '#barcode { position:absolute; top:140px; left:680px; padding:0px; }\n'+
        'img { padding:0px; }\n'+
        'img.barcode { border: 0px solid gray; }\n';
    }

    if (module == 'bankperso' && report == 'materials') 
    {
        report_body += 

        '.materials { font-size:12px; }\n'+
        '.materials dl { font-size:16px; font-weight:bold; line-height:24px; margin-bottom:40px; }\n'+
        '.materials dt { float:left; width:120px; padding-left:40px; }\n'+
        '.materials dd { float:left; }\n'+
        '.materials table.data { border-spacing:0px; font-size:12px; width:100%; }\n'+
        '.materials .header td { padding:10px 5px 10px 5px; text-align:center; font-size:14px; font-weight:bold; }\n'+
        '.materials .header td.col0 { text-align:left; }\n'+
        '.materials .header td.col2 { text-align:left; }\n'+
        '.materials td.value { padding:5px; border-bottom:2px solid black; }\n'+
        '.materials td.col0 { width:150px; }\n'+
        '.materials td.col2 { width:400px; }\n'+
        '.materials td.name { color:#237; font-weight:bold; }\n'+

        '.total { font-size:14px; font-weight:bold; line-height:40px; white-space:nowrap; }\n';
    }

    if (module == 'bankperso' && report == 'containerlist') 
    {
        report_body += 

        '.containerlist { font-size:12px; }\n'+
        '.containerlist table.data { border-collapse:collapse; border-spacing:0px; font-size:inherit; martin-top:10px; width:100%; }\n'+
        '.containerlist td { padding:1px 5px 1px 5px; border:1px solid #ccc; }\n'+
        '.containerlist td.caption { text-align:center; font-size:16px; font-weight:bold; white-space:nowrap; }\n'+
        '.containerlist td.header { text-align:center; white-space:normal; }\n'+
        '.containerlist td.col0 { width:160px; }\n'+
        '.containerlist td.col1 { width:80px; }\n'+
        '.containerlist td.col2 { width:140px; }\n'+
        '.containerlist td.col3 { width:80px; }\n'+
        '.containerlist td.col4 { width:60px; }\n'+
        '.containerlist td.col5 { width:100px; }\n'+
        '.containerlist td.col6 { width:80px; }\n'+
        '.containerlist td.col7 {}\n'+
        '.containerlist tr.section>td { border-top:2px solid black; }\n'+
        '.containerlist td.name { font-size:11px; font-weight:bold; }\n'+
        '.containerlist td.value { font-weight:bold; }\n'+
        '.containerlist tr.item>td.value { border-style:none; }\n'+
        '.containerlist tr.item>td.value>div { border:1px solid #666; padding:2px; }\n'+
        '.containerlist tr.total>td { font-weight:bold; }\n'+
        '.containerlist tr.total>td.value { border:2px solid black !important; }\n'+
        '.containerlist tr.sign>td { background-color:#f7f7f7; }\n'+

        '.batches { font-weight:bold; padding:10px 0 10px 0; }\n'+
        '.batches p { margin:0; padding:0 0 5px 0; }\n';
    }

    report_body += 
        '</style>\n'+
        '</head><body>\n';
}

function makeBankperso_TZ(div) {
    var now = new Date().toLocaleString().replace(',', '');

    report_body +=
        '<h2 class="right">'+now.toString()+'</h2>\n'+
        '<div class="content">'+div.html().replace(/none/gi, 'block')+'</div><br>\n'+
        '';    
}

function makeBankperso_Materials(data, props) {
    var now = new Date().toLocaleString().replace(',', '');

    report_body +=
        '<h2 class="right">'+now.toString()+'</h2>\n'+
        '<div class="page landscape materials">'+
          '<h1 class="center">Заявка на расходные материалы</h1>'+
          '<dl>\n'+
            '<dt class="title">Заказ:</dt><dd class="value">'+props['ClientName']+'</dd><br>\n'+
            '<dt class="title">Файл заказа:</dt><dd class="value">'+props['FileName']+'</dd>\n'+
          '</dl>\n'+
          '<table class="data">'+
          '<tr class="header">';

    var columns = props['headers'];

    for(var j=0; j < columns.length; j++) {
        report_body += '<td class="col'+j+'">'+columns[j]+':</td>';
    }

    report_body += '</tr>';

    var rows = data;

    for(var i=0; i < rows.length; i++) {
        var row = rows[i];
        
        report_body += 
          '<tr>'+
            '<td class="value nowrap">'+row['BatchType']+'</td>'+
            '<td class="value nowrap center">'+row['BatchQty']+'</td>'+
            '<td class="value name">'+row['MName']+'</td>'+
            '<td class="value nowrap center">'+row['Qty']+'</td>'+
          '</tr>';
    }

    report_body += 
          '<tr class="total">'+
            '<td>Итого позиций: <span>'+props['total'][0]+'</span></td>'+
            '<td class="center">'+props['total'][1]+'</td>'+
            '<td></td>'+
            '<td class="center">'+props['total'][2]+'</td>'+
          '</tr>';

    report_body +=
          '</table>'+
        '</div>';
}

function makeBankperso_ContainerList(data, props) {
    var now = new Date().toLocaleString().replace(',', '');
    var empty_value = '&nbsp;';
    var empty_column = '<td>'+empty_value+'</td>';

    function _empty(n) {
        var x = '';
        for(var i=0; i < n; i++) x += empty_column;
        return x;
    }

    function _blank_row(cls, s) {
        var x = 
          '<tr class="'+cls+'">'+
            '<td>'+s+'</td>'+
            _empty(7)+
          '</tr>';
        return x;
    }

    report_body +=
        '<div class="page portrait containerlist">'+
          '<table class="data">'+
          '<tr>'+
            '<td class="center" rowspan="2">Контейнер</td>'+
            '<td class="caption" colspan="7">'+props['ClientName']+'</td>'+
          '</tr>'+
          '<tr>'+
            '<td class="caption" colspan="7">'+props['FileName']+'</td>'+
          '</tr>'+
          '<tr class="section">';

    var columns = '|Кол-во|Фамилия|Подпись|Номер печати|Фамилия|Подпись|Дата/время'.split('|');

    for(var j=0; j < columns.length; j++) {
        report_body += '<td class="header col'+j+'">'+(columns[j].length > 0 ? columns[j] : empty_value)+'</td>';
    }

    report_body += 
          '</tr>'+
          '<tr class="sign">'+
            '<td class="center" colspan="5">СКЛАД передал</td>'+
            '<td class="center" colspan="3">Диспетчер проверил</td>'+
          '</tr>';

    var items = props['items'];

    for(var i=0; i < items.length; i++) {
        var item = items[i];
        
        report_body += 
          '<tr class="item">'+
            '<td class="name">'+item+'</td>'+
            '<td class="value nowrap center"><div>'+data[item]+'</div></td>'+
            _empty(5)+
            '<td class="nowrap center">'+now+'</td>'+
          '</tr>';
    }

    report_body += _blank_row('section', 'Доп. Карта');
    report_body += _blank_row('', 'Доп. Карта');

    report_body += 
          '<tr class="total">'+
            '<td>Итого:</td>'+
            '<td class="value center">'+props['FQty']+'</td>'+
            _empty(6)+
          '</tr>';

    report_body += 
          '<tr class="sign">'+
            '<td class="nowrap center" colspan="5">ОператорПерсонализации пересчитал</td>'+
            '<td class="nowrap center" colspan="3">ОператорПерсонализации проверил</td>'+
          '</tr>';

    report_body += _blank_row('', 'Тираж');
    report_body += _blank_row('', 'Брак');
    report_body += _blank_row('', 'Остаток хороших');

    report_body += 
          '<tr class="sign">'+
            '<td class="nowrap center" colspan="5">Раскладка пересчитал</td>'+
            '<td class="nowrap center" colspan="3">Раскладка проверил</td>'+
          '</tr>';

    report_body += _blank_row('', 'Тираж');
    report_body += _blank_row('', 'Брак');
    report_body += _blank_row('', 'Остаток хороших');

    report_body += 
          '<tr class="sign">'+
            '<td class="nowrap center" colspan="5">Раскладка(сдал)</td>'+
            '<td class="nowrap center" colspan="3">Склад(принял)</td>'+
          '</tr>';

    report_body += _blank_row('', 'Тираж');
    report_body += _blank_row('', 'Брак');
    report_body += _blank_row('', 'Остаток хороших');
    report_body += _blank_row('', 'Образцы');

    report_body += 
          '<tr>'+
            '<td class="" colspan="8">Примечание:'+'<div class="batches">'+props['TZ']+'</div></td'+
          '</tr>';

    report_body +=
          '</table>'+
        '</div>';
}

function makeCardsReport_1(data, props, page_break, mode) {

    report_body +=
        '<div class="page landscape '+(page_break ? 'page-break' : '')+' r1">';

    report_body +=
          '<h1 class="center underline">'+props['ClientName']+'</h1>'+
          '<table class="caption" border="0"><tr>'+
            '<td><h2 class="center">Заявка на выдачу заготовок пластиковых карт на банковскую персонализацию на</h2></td>'+
            '<td><div class="r1_now sharping">'+props['Now']+'</div></td></tr></table>'+
          '<div class="inline title">'+
            '<div class="left">Имя файла:<span class="filename sharping">'+props['FileName']+'</span></div>'+
            '<div class="right readydate">Ожидаемая дата отгрузки:<span class="high sharping readydate">'+props['ReadyDate']+'</span></div></div>'+
          '<table class="data">'+
          '<tr>';

    var columns = '№ конт.|Наименование карт|Вид карт|Тип карт|ERP_TZ|№ ТЗ / партии|Кол-во|Тип партии|Срочность|Сум.'.split('|');

    for(var j=0; j < columns.length; j++) {
        report_body += '<td class="header">'+columns[j]+'</td>';
    }

    report_body += '</tr>';

    var rows = data[mode];
    var rowspan = '';
    var in_row = false;

    function set_column(value, rowspan, in_row, cls) {
        var column = '<td class="value'+(!is_empty(cls) ? ' '+cls :'')+'"'+rowspan+'>'+value+'</td>';
        return !is_empty(rowspan) ? (!is_empty(value) || in_row ? column : '') : column;
    }

    for(var i=0; i < rows.length; i++) {
        var row = rows[i];
        var n = (i+1).toString();
        var in_row = ('rowspan' in row) ? true : false;

        if (in_row)
            rowspan = (row['rowspan'] > 0) ? ' rowspan="'+row['rowspan'].toString()+'"' : '';

        report_body += 
          '<tr>'+
            '<td class="value np">'+n+'</td>'+
            set_column(row['CardsName'], rowspan, in_row)+
            set_column(row['CardsType'], rowspan, in_row)+
            set_column(row['PlasticType'], rowspan, in_row)+
            '<td class="value">'+row['ERP_TZ']+'</td>'+
            '<td class="value nowrap">'+row['SysBatchID']+' / '+row['PersBatchID']+'</td>'+
            '<td class="value">'+row['BQty']+'</td>'+
            '<td class="value">'+row['PersBatchType']+'</td>'+
            '<td class="value nowrap">'+row['Urgency']+'</td>'+
            set_column(row['SumQty'], rowspan, in_row, 'sumqty')+
          '</tr>';
    }

    var sign = Array(51).join("_"); //"_".repeat(50);

    report_body +=
          '<tr>'+
            '<td colspan="6"><span class="keyword">ИТОГ:</span></td><td colspan="4">'+
              '<span class="total">'+props['Total']+'</span>'+
            '</td>'+
          '</tr>'+
          '</table>'+
          '<table class="footer" border="0"><tr><td>'+
            '<div class="left">Администратор БД<span class="sign">'+sign+'</span></div>'+
            '<div class="left">Начальник отдела персонализации<span class="sign">'+sign+'</span></div>'+
            '<div class="left">Выдал кладовщик<span class="sign">'+sign+'</span></div>'+
          '</td><td>'+
            '<div class="right final">Получил<span class="sign">'+sign+'</span></div>'+
          '</td></tr></table>'+
        '</div>';
}

function makeCardsReport_2(props, page_break) {

    report_body +=
        '<div class="page landscape '+(page_break ? 'page-break' : '')+' r2">';

    function make_caption(i) {
        var page_break = i > 0 ? ' style="page-break-before:always;"' : '';

        report_body +=
          '<table border="0"'+page_break+'><tr>'+
            '<td style="width:700px"><h1 class="left">Задание на персонализацию карт</h1></td>'+
            '<td><div class="right bold r2_now" style="">'+props['Now']+'</div></td></tr></table>';
    }

    var columns = 'Клиент|№ ТЗ|№ партии|Тип партии|Кол-во карт(ТЗ)|Кол-во карт(партия)'.split('|');
    var width = new Array(160,100,100,200,140,140);
    var ids = props['ids'];
    var batches = props['batches'];
    var opers = props['opers'];

    for(var i=0; i < ids.length; i++) {
        var id = ids[i];

        if (i%3 == 0)
            make_caption(i);

        report_body +=
          '<div class="r2_box">'+
            '<table class="r2_data">'+
            '<tr>';

        for(var j=0; j < columns.length; j++) {
            report_body += 
              '<td class="title center" style="width:'+width[j].toString()+'px">'+columns[j]+'</td>';
        }

        report_body += 
            '</tr>';

        var row = batches[id];

        report_body += 
            '<tr class="data">'+
              '<td class="center">'+row['Client']+'</td>'+
              '<td class="center">'+row['TZ']+'</td>'+
              '<td class="center">'+row['TID']+'</td>'+
              '<td class="center">'+row['PersType']+'</td>'+
              '<td class="center">'+row['BQty']+'</td>'+
              '<td class="center">'+row['PQty']+'</td>'+
            '</tr>'+
            '</table>';

        report_body +=
            '<table class="r2_sign">'+
            '<tr>'+
              '<td class="title center" style="width:145px">Тип операции</td>'+
              '<td class="title center" style="width:145px">Подпись оператора</td>'+
              '<td class="center bold" style="background-color:#aaa;font-size:14px;">Файл заказа:</td>'+
              '<td class="title left">'+props['FileName']+'</td>'+
            '</tr>'+
            '</table>';

        report_body +=
          '</div>';

        var row = opers[id];

        report_body +=
          '<div class="r2_footer">';

        for(var j=0; j < row.length; j++) {
            report_body += '<h3 class="left sharping">'+row[j]+'</h3>';
        }

        report_body +=
          '</div>';
    }

    report_body +=
        '</div>';
}

function makeCardsReport_3(props, page_break, single_page) {

    report_body +=
        '<div class="page portrait '+(page_break ? 'page-break' : '')+' r3">';

    var columns = '|Наименование теста|Периодичность|Ответственный|Подпись|Документ: Стандарт качества карточной продукции ПС "МИР"/РД 53-2016|Спецификация шаблон|Подпись|Примечание'.split('|');
    var width = new Array(30,100,100,80,80,80,120,100,70);
    var cols = columns.length;
    var cls_count = 4;

    var rows = [
        '1|Кол-во ТЗ / Кол-во карт во всех ТЗ.|100%|Оператор||Должностная инструкция||',
        '2|Сверка дизайна|100%|Оператор||||',
        '3|Габариты карты после рельефного тиснения|5 карт/смену|Оператор||14.1.1.1. ГОСТ ИСО/МЭК 10373-1|ширина:85,47-85,90 мм высота:53,92-54,18 мм толщина вне зоны тисения 0,76-0,84 мм|',
        '||5 карт/смену|Контролер||||',
        '4|Расположение тесненных символов|1 карта/смену|||14.1.1.2. ИСО/МЭК 7811-1|Шаблон|',
        '||1 карта/смену|||||',
        '5|Размеры тесненных символов|при новом оборудовании и новых шрифтов|Оператор||14.1.1.3. ИСО/МЭК 7811-1|Сертификат производителя перонализационной машины|Длина 4,32 мм(номин) Ширина 2, 54 мм (номин) Ширина штриха 0,51 ± 0,26',
        '|||Контролер||||',
        '6|Высота рельефа тесненных символов|1 карта/смену|Оператор||14.1.1.4. ИСО/МЭК 7811-1|не более 0,46 мм для визуального чтения|',
        '|||Контролер||||',
        '7|Окраска рельефа символов|1 единица/партии|Оператор||14.1.1.5.|визуальный осмотр|',
        '|||Контролер||||',
        '8|Износостойкость окраски рельефных символов|1 единица/смену|Оператор||14.1.1.6. TM-P- 001|клейкая лента 2,5 Н/см  ISO 2409 Ждать 1 мин, далее снять под углом 60 ° |',
        '||1 единица/смену|Контролер||||',
        '9|Целостность символов, напечатанных термотрансферным методом|1 единица/100|Оператор||14.1.2.1. ПС "МИР" TM-P-004|Визуальный осмотр нанесения печати шрифта (полное, стабильное, без наслоения)|',
        '||1 единица/100|Контролер||||',
        '10|Индент-печать-внешний вид|1 единица/партии|Оператор||14.1.3.1.|визуальный осмотр|',
        '||1 единица/партии|Контролер||||',
        '11|Индент-печать на лицевой стороне карты|1 единица/партии|Оператор||14.1.3.2.|визуальный осмотр|',
        '||1 единица/партии|Контролер||||',
        '12|Индент-печать. Расположение символов на панели для подписи|1 единица/партии|Оператор||14.1.3.3.|визуальный осмотр|',
        '||1 единица/партии|Контролер||||',
        '13|Окраска символов при индент печати|1 единица/партии|Оператор||14.1.3.4.|визуальный осмотр|',
        '||1 единица/партии|Контролер||||',
        '14|Целостность символов, нанесенных методом индент-печати|1 единица/партии|Оператор||14.1.3.5 TM-P-004|Визуальный осмотр нанесения печати шрифта (полное, стабильное, без наслоения)|',
        '||1 единица/партии|Контролер||||',
        '15|Характеристики записи магнитной полосы |1 единица/партии|Оператор||14.2.1.1.ИСО/МЭК 7811-6| MAG-TESTER Проверка параметров: Плотность записи; Амплитуда сигнала, Расп.стартового символа; Джиттер - нежелательные фазовые отклонения.|',
        '||1 единица/партии|Контролер||||',
        '16|Расположение треков|1 единица/партии|Оператор||14.2.1.2. ИСО/МЭК 7811-6 TM-P-009|Проверка фактического расположения записи двух или трех дорожек при помощи проявителя и прозрачного шаблона. |',
        '||1 единица/партии|Контролер||||',
        '17|Характеристики электрической персонализации|1 единица/партии|Оператор||14.2.2.1. ИСО/МЭК 7811-6/7816-1|Проверка аккредитованным средством испытания (EMV Insight/АРМ "МИР")|',
        '||1 единица/партии|Контролер||||',
        '18|ATR (Answer to Reset) и CPLC |100%|Оператор||14.2.2.2. ИСО/МЭК 7816-3|100% проверка проводится на Maxsys/Mx-1000|',
        '||100%|Контролер||||',
        '19|Характеристики электромагнитной персонализации|1 единица/партии|Оператор||14.2.3.1. ИСО/МЭК 14443-1|SBSK 03 (ПО для проверки бесконтактной кодировки)|',
        '||1 единица/партии|Контролер||||',
        '20|Проверка параметра ATS (Answer to Select) после графической персонализации|100%|Оператор||14.2.3.2. ИСО/МЭК 14443-3 EMV |100% проверка проводится на Maxsys|',
        '||100%|Контролер||||',
        '21|Отсутствие механических деформаций карты после персонализации|1 единица/партии|Оператор||14.2.4.1.TM-P-003|Провести визуальный осмотр Лупой 10X всех рельефных и печатных симоволов на предмет трещин|',
        '||1 единица/партии|Контролер||||',
        '22|Коробление карты после персонализации|1 единица/1000|Оператор||14.2.4.2. ИСО/МЭК 10373-TM-СВ-018 |Специальное устройство - пластина. Допуски в критичной точке удаления от пластины <=1,5 мм/Горка с уровнем допуска.|',
        '||1 единица/1000|Контролер||||',
        '23|Проверка соответствий|1 единица/партии|Оператор||14.2.5.1. ПС "МИР"|Проверка корректности соответствия:Электрической, электромагнитной, М/П, Эмбоссирования, Индент печати, Термотрансферной, Лазерной гравировки|',
        '||1 единица/партии|Контролер||||'
    ];

    function makeHeader(n) {
        var page_break_after = ''; //(n > 1 && n < 10) ? ' style="page-break-after:always;"' : '';

        report_body +=
          '<h1 class="center">Протокол проверки карточной продукции "МИР"</h1>'+
          '<h2 class="center"><span class="caption">'+props['FileName']+'</span> от <span class="caption">'+props['Today']+'</span></h1>'+
          '<div class="r3_box"'+page_break_after+'>'+
            '<table class="r3_data">'+
            '<tr>';

        for(var j=0; j < cols; j++) {
            report_body += '<td class="header col'+j+'">'+columns[j]+'</td>';
        }

        report_body += 
            '</tr>';
    }

    function makeRowspan2(i, j) {
        return ([0,1,5,6].indexOf(j) > -1 || ([2,7].indexOf(j) > -1 && [6,8,10].indexOf(i) > -1)) ? true : false;
    }

    attrs = {
        'width'     : width,
        'cols'      : cols,
        'cls_count' : cls_count,
        'page_break': [20,26], 
    };

    make_cards_protocol(single_page, columns, rows, attrs, makeHeader, makeRowspan2);
}

function makeCardsReport_4(props, page_break) {

    report_body +=
        '<div class="page landscape '+(page_break ? 'page-break' : '')+' r4">';

    report_body +=
          '<h1 class="center underline">'+props['ClientName']+'</h1>'+
          '<h2 class="center">Общее задание на печать листовок</h2>'+
          '<h2 class="center">№ <span class="caption">'+props['FileName']+'</span> от <span class="caption">'+props['Now']+'</span></h1>'+
          '<table class="data">'+
          '<tr>';

    var columns = '№ ТЗ / партии|Кол-во|Листовка'.split('|');

    for(var j=0; j < columns.length; j++) {
        report_body += '<td class="header col'+j+'">'+columns[j]+'</td>';
    }

    report_body += '</tr>';

    var rows = props['blanks'];

    for(var i=0; i < rows.length; i++) {
        var row = rows[i];
        
        report_body += 
          '<tr>'+
            '<td class="value nowrap">'+row['SysBatchID']+' / '+row['PersBatchID']+'</td>'+
            '<td class="value">'+row['BQty']+'</td>'+
            '<td class="value">'+row['Blank']+'</td>'+
          '</tr>';
    }

    report_body +=
          '</table>'+
        '</div>';
}

function makeCardsReport_5(props, page_break, single_page) {

    report_body +=
        '<div class="page portrait '+(page_break ? 'page-break' : '')+' r5">';

    var columns = '№ <nobr>п/п</nobr>|Документ|Наименование теста|Периодичность|Ответственный|Результат <nobr>(Y/N/Значение)</nobr>|Подпись|Примечание'.split('|');
    var width = new Array(40,80,120,80,80,80,80,100);
    var cols = columns.length;
    var cls_count = 3;

    var rows = [
        '1|Должностная инструкция|Кол-во ТЗ/Кол-во карт во всех ТЗ|100%|Оператор|||',
        '2|Должностная инструкция|Соответствие дизайна карты ТЗ|100%|Оператор|||',
        '|||100%|Контролер|||',
        '3|R-BG-02, РД 052-2013 п.1.2|Местоположение эмбоссированных символов|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '4|R-BG-03, РД 052-2013 п.1.3|Размеры символов после эмбоссирования, соответствие ISO 7811-1|1 карта/файл|Оператор|||',
        '|||1 карта/файл|Контролер|||',
        '5|R-BG-04, РД 052-2013 п.1.4|Высота символов после эмбоссирования (0,36-0,46 мм max)|1 карта/файл|Контролер|||',
        '6|R-BG-05, РД 052-2013 п.2|Цвет типирования согласно ТЗ|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '7|R-BG-08, РД 052-2013 п.3|Целостность термотрансферных символов|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '8|R-BG-10, РД 052-2013 п.4|Внешний вид символов индент печати (веден ли задний индент на лицевой стороне карты)|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '9|R-BG-11, РД 052-2013 п.4.1|Индент печать на лицевой стороне карты|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '10|R-BG-12, РД 052-2013 п.4.2|Местоположение символов индент печати|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '11|R-BG-13, РД 052-2013 п.4.3|Цвет индент печати на оборотной стороне карты чёрный|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '12|R-BG-14, РД 052-2013 п.4.4|Целостность символов индент печати|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '13|R-BF-01-2, РД 052-2013 п.7|Проверка электрической кодировки чипа|100%|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '14|R-BF-01-3, РД 052-2013 п.8|Проверка электромагнитной кодировки чипа|100%|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '15|R-BR-06, РД 052-2013 п.11|Проверка идентичности графической, электрической, электромагнитной персонализации|1 карта/ТЗ|Оператор|||',
        '|||1 карта/ТЗ|Контролер|||',
        '16|R-BR-01, РД 052-2013 п.9|Тест на отсутствие остаточных напряжений|1 карта/файл|Контролер|||',
        '17|R-P5-01, РД 052-2013 п.10|Полное коробление карты|1 карта/файл|Контролер|||',
        '18|R-F1-06, РД 052-2013 п.12|Ответ контактного чипа|100%|Оператор|||',
        '19|R-F1-17, РД 052-2013 п.13|Ответ бесконтактного чипа|100%|Оператор|||',
        '20|R-BF-01-1|Расположение треков магнитной полосы|1 карта/файл|Контролер|||',
        '||Проверка характеристик кодирования магнитной полосы (Bit density, Signal amplitude, Start sentinel, jitter)|1 карта/ТЗ|Оператор|||',
        '21|R-BG-06, РД 052-2013 п.2.1|Долговечность типпинга|1 карта/файл|Контролер|||',
        '22|Должностная инструкция|Соответствие персонализации карты ТЗ и ПЗ|1 карта/ТЗ|Контролер|||'
    ];

    function makeHeader(n) {
        var page_break_after = ''; // n < 10 ? ' style="page-break-after:always;"' : '';

        report_body +=
          '<h1 class="center">Протокол проверки карт</h1>'+
          '<h2 class="center"><span class="caption">'+props['FileName']+'</span> от <span class="caption">'+props['Today']+'</span></h1>'+
          '<div class="r5_box"'+page_break_after+'>'+
            '<table class="r5_data">'+
            '<tr class="header">';

        for(var j=0; j < cols; j++) {
            report_body += '<td class="col'+j.toString()+'">'+columns[j]+'</td>';
        }

        report_body += 
            '</tr>';
    }

    function makeRowspan2(i, j) {
        return ([0,1].indexOf(j) > -1 || ([32,33].indexOf(i) == -1 && j == 2)) ? true : false;
    }

    attrs = {
        'width'     : width,
        'cols'      : cols,
        'cls_count' : cls_count,
        'page_break': [22], 
    };

    make_cards_protocol(single_page, columns, rows, attrs, makeHeader, makeRowspan2);
}

function make_cards_protocol(single_page, columns, rows, attrs, make_header, make_rowspan2) {

    var scheme = 1;
    var n = 0;
    var rowspan = new Array();

    var cols = attrs['cols'];
    var cls_count = attrs['cls_count'];
    var width = attrs['width'];
    var page_break = attrs['page_break'];

    function get_column(i, j, value, cls, rowspan) {
        var _pos = i.toString()+':'+j.toString();
        var _class = (cls ? cls : '')+(j > 0 && j < cls_count ? ' high' : '');
        var _rowspan = rowspan ? ' '+rowspan : '';
        var _value = is_null(value) ? '' : value;
        return '<td pos="'+_pos+'" class="'+_class+'"'+_rowspan+'>'+_value+'</td>';
    }

    for(var i=0; i < rows.length; i++) {
        var row = rows[i].split('|');
        var next_row = (i < rows.length-1) ? rows[i+1].split('|')[0] : null;

        n += (scheme == 1 ? 1 : 0);

        if (scheme == 1) {
            if (n == 1)
                make_header(n);

            else if (!single_page && page_break.indexOf(n) > -1) {
                report_body += '</table></div>';
                make_header(n);
            }
        }

        report_body += '<tr>';

        if (scheme == 2) {
            for(var j=0; j < cols; j++) {
                var value = j < row.length ? row[j] : '';
                var cls = 'value col'+j.toString();

                if (value.length == 0) {
                    if (rowspan.indexOf(j) == -1)
                        report_body += get_column(i, j, value, cls);
                }
                else
                    report_body += get_column(i, j, value, cls);
            }

            scheme = 1;
        }
        else if (row[0].length > 0) {
            if (is_null(next_row))
                scheme = 0;
            else if (next_row.length == 0)
                scheme = 2;
            else
                scheme = 1;

            rowspan = [];
            
            for(var j=0; j < cols; j++) {
                var value = (j < row.length) ? row[j].toString() : '';
                var cls = 'value col'+j.toString();

                if (value.length == 0)
                    report_body += get_column(i, j, value, cls);
                else if (scheme == 2 && make_rowspan2(i, j)) {
                    report_body += get_column(i, j, value, cls, 'rowspan="2"');
                    rowspan.push(j);
                }
                else
                    report_body += get_column(i, j, value, cls);
            }
        }

        report_body +=
            '</tr>';
    }

    report_body +=
            '</table>';

    var sign = Array(51).join("_");

    report_body +=
            '<div class="r35_sign">'+
              '<h4 class="left">Вывод: Партия карт соответствует / не соответствует требованиям нормативно-технической документации.</h2>'+
              '<h4 class="left">Комментарии:<span class="sign">'+sign+'</span></h4>'+
            '</div>'+
          '</div>'+
        '</div>';

    return report_body;
}

function printReport(show) {
    var w = window.open('', '_blank'); //'', 'PRINT', 'height=800,width=800'

    report_body +=
        '</body></html>';

    w.document.open();
    w.document.writeln('<!DOCTYPE html>');
    w.document.write(report_body);
    w.document.close();

    if (show == 0) {
        w.print();

        if (!isIE) w.close();
    }
}


