# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
import math
from pytils import numeral

from openerp.report import report_sxw
from openerp.tools.float_utils import float_round

class m15(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context=None):
        super(m15, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'count_of_sm': self.get_count_stock_moves_in_text,
            'price_in_text': self.get_price_in_text,
            'price_cop': self.get_price_cop,
            'tax_all': self.get_tax,
            'tax_cop': self.get_tax_cop,
            
        })
    
    def get_price_in_text(self, picking_id):
        sum_all=0.0
        picking = self.pool.get('m15').browse(self.cr, self.uid, picking_id)
        for move in picking.move_lines:
            sum_all=sum_all + move.price_all     
        return numeral.in_words(int(sum_all))  
    
    def get_price_cop(self, picking_id):
        sum_all=0.0
        picking = self.pool.get('m15').browse(self.cr, self.uid, picking_id)
        for move in picking.move_lines:
            sum_all=sum_all + move.price_all
        result = str(int(math.modf(sum_all)[0] * 100))
        if len(result) < 2:
            result = '0'+result      
        return result
    
    
    def get_tax(self, picking_id):
        t_all=0.0
        picking = self.pool.get('m15').browse(self.cr, self.uid, picking_id)
        for move in picking.move_lines:
            tax_all=0.0
            tax_all = move.amount_tax * move.product_qty 
            t_all=t_all + tax_all            
        return int(t_all)
      
    def get_tax_cop(self, picking_id):
        t_all=0.0
        picking = self.pool.get('m15').browse(self.cr, self.uid, picking_id)
        for move in picking.move_lines:
            tax_all=0.0
            tax_all = move.amount_tax * move.product_qty 
            t_all=t_all + tax_all
        r = str(int(math.modf(t_all)[0] * 100) )
        if len(r) < 2:
            r = '0'+r          
        return r      
    
    def get_count_stock_moves_in_text(self, picking_id):
        picking = self.pool.get('m15').browse(self.cr, self.uid, picking_id)
        count = len(picking.move_lines)
        return numeral.in_words(count, numeral.NEUTER)


    # register the new report service :
report_sxw.report_sxw('report.m15','m15', 'addons/m15/report/m15.rml', parser=m15)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

