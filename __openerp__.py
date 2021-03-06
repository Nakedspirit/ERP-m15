# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': "M-15",
    'author': "Galinka",
    'complexity': "easy",
    'version': "1.0",
    'depends': ['base','sale','account','mrp', 'oksm', 'okv', 'okei'],
    'category' : "Dictionaries",
    'description': """
    M-15 module.
    """,
    'init_xml': [],
    'data': [

        'wizard/stock_partial_picking_view.xml',
        
        'm15_view.xml',
        'm15_sequence.xml',
        'm15_workflow.xml',
        'm15_report.xml',
    
    ],
    'installable': True,
#    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
