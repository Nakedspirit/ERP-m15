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

import time

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import netsvc
import openerp.addons.decimal_precision as dp

from openerp.tools.float_utils import float_round




class m15(osv.Model):
    _name = 'm15'
    _inherit = 'stock.picking'
#     _table = "m15"
    _description = "M15"

    
    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms picking.
        @return: True
        """
        pickings = self.browse(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'confirmed'})
        todo = []
        for picking in pickings:
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        todo = self.action_explode(cr, uid, todo, context)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)
        return True
    
    def action_process(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        """Open the partial picking wizard"""
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }    
    
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        picking_obj = self.browse(cr, uid, id, context=context)
        move_obj = self.pool.get('stock.move')
        if ('name' not in default) or (picking_obj.name == '/'):
            seq_obj_name = 'stock.picking.' + picking_obj.type
            default['name'] = self.pool.get('ir.sequence').get(cr, uid, seq_obj_name)
            default['origin'] = ''
            default['backorder_id'] = False
        if 'invoice_state' not in default and picking_obj.invoice_state == 'invoiced':
            default['invoice_state'] = '2binvoiced'
        res = super(m15, self).copy(cr, uid, id, default, context)
        if res:
            picking_obj = self.browse(cr, uid, res, context=context)
            for move in picking_obj.move_lines:
                move_obj.write(cr, uid, [move.id], {'tracking_id': False, 'prodlot_id': False, 'move_history_ids2': [(6, 0, [])], 'move_history_ids': [(6, 0, [])]})
        return res

    def onchange_partner_in(self, cr, uid, ids, partner_id=None, context=None):
        return {}

    def action_explode(self, cr, uid, moves, context=None):
        """Hook to allow other modules to split the moves of a picking."""
        return moves


    def test_auto_picking(self, cr, uid, ids):
        # TODO: Check locations to see if in the same location ?
        return True

    
    
    def action_assign(self, cr, uid, ids, *args):
        """ Changes state of picking to available if all moves are confirmed.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            if pick.state == 'draft':
                wf_service.trg_validate(uid, 'm15', pick.id, 'button_confirm', cr)
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            if not move_ids:
                raise osv.except_osv(_('Warning!'),_('Not enough stock, unable to reserve the products.'))
            self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True

    def force_assign(self, cr, uid, ids, *args):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed','waiting']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'm15', pick.id, cr)
        return True

    def draft_force_assign(self, cr, uid, ids, *args):
        """ Confirms picking directly from draft state.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            if not pick.move_lines:
                raise osv.except_osv(_('Error!'),_('You cannot process picking without stock moves.'))
            wf_service.trg_validate(uid, 'm15', pick.id,
                'button_confirm', cr)
        return True

    def draft_validate(self, cr, uid, ids, context=None):
        """ Validates picking directly from draft state.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        self.draft_force_assign(cr, uid, ids)
        for pick in self.browse(cr, uid, ids, context=context):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'm15', pick.id, cr)
        return self.action_process(
            cr, uid, ids, context=context)
        
    def cancel_assign(self, cr, uid, ids, *args):
        """ Cancels picking and moves.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').cancel_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'm15', pick.id, cr)
        return True
    
    
    
    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Changes picking state to assigned.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'assigned'})
        return True

    def test_finished(self, cr, uid, ids):
        """ Tests whether the move is in done or cancel state or not.
        @return: True or False
        """
        move_ids = self.pool.get('stock.move').search(cr, uid, [('m15_id', 'in', ids)])
        for move in self.pool.get('stock.move').browse(cr, uid, move_ids):
            if move.state not in ('done', 'cancel'):

                if move.product_qty != 0.0:
                    return False
                else:
                    move.write({'state': 'done'})
        return True

    def test_assigned(self, cr, uid, ids):
        """ Tests whether the move is in assigned state or not.
        @return: True or False
        """
        #TOFIX: assignment of move lines should be call before testing assigment otherwise picking never gone in assign state
        ok = True
        for pick in self.browse(cr, uid, ids):
            mt = pick.move_type
            # incomming shipments are always set as available if they aren't chained
            if pick.type == 'in':
                if all([x.state != 'waiting' for x in pick.move_lines]):
                    return True
            for move in pick.move_lines:
                if (move.state in ('confirmed', 'draft')) and (mt == 'one'):
                    return False
                if (mt == 'direct') and (move.state == 'assigned') and (move.product_qty):
                    return True
                ok = ok and (move.state in ('cancel', 'done', 'assigned'))
        return ok

    def action_cancel(self, cr, uid, ids, context=None):
        """ Changes picking state to cancel.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        return True

    #
    # TODO: change and create a move if not parents
    #
    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done.
        
        This method is called at the end of the workflow by the activity "done".
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_move(self, cr, uid, ids, context=None):
        """Process the Stock Moves of the Picking
        
        This method is called by the workflow by the activity "move".
        Normally that happens when the signal button_done is received (button 
        "Done" pressed on a Picking view). 
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            todo = []
            for move in pick.move_lines:
                if move.state == 'draft':
                    self.pool.get('stock.move').action_confirm(cr, uid, [move.id],
                        context=context)
                    todo.append(move.id)
                elif move.state in ('assigned','confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.pool.get('stock.move').action_done(cr, uid, todo,
                        context=context)
        return True

    

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id in product_avail:
                        product_avail[product.id] += qty
                    else:
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                move_currency_id, product_price)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                product.uom_id.id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])\
                                + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency})


            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,'m15.%s'),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'm15_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'m15_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'm15', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'm15', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'm15', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'm15', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res


 
    _columns = {
        'backorder_id': fields.many2one('m15', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('waybill', 'Shipped Goods') ], 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
        'activity_sender': fields.char('Business activity sender', size=128, required=True, translate=True),
        'allowed_position': fields.char('Shipment allowed: Position', size=128, translate=True),
        'allowed_name': fields.char('Shipment allowed: Name', size=128, translate=True),
        'considered_position': fields.char('Shipment considered: Position', size=128, translate=True),
        'considered_name': fields.char('Shipment considered: Name', size=128, translate=True),
        'released_position': fields.char('Position the issuing', size=128, translate=True),
        'released_name': fields.char('Name the issuing', size=128, translate=True),
        'received_position': fields.char('Receiving position', size=128, translate=True),
        'received_name': fields.char('Receiving name', size=128, translate=True),
        'move_lines': fields.one2many('stock.move', 'm15_id', 'Internal Moves', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        }
            
    
    _defaults = {'type': 'waybill',}

   
m15()




class account_tax_m15(osv.osv):
    _name = 'account.tax.m15'
    _inherit = 'account.tax'
      
    _columns = {
        'standard_price': fields.related('product_id', 'standard_price', type='float'),
        'quantity': fields.related('product_id', 'product_qty', type='float'),
               }
      
      
      
    def _applicable(self, cr, uid, taxes, standard_price, product=None, partner=None):
        res = []
        for tax in taxes:
            if tax.applicable_type=='code':
                localdict = {'standard_price':standard_price, 'product':product, 'partner':partner}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res
      
      
    def _unit_compute(self, cr, uid, taxes, standard_price, product=None,  quantity=0):
        taxes = self._applicable(cr, uid, taxes, standard_price ,product)
        res = []
        cur_standard_price=standard_price
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            data = {'id':tax.id,
                    'name':tax.description and tax.description + " - " + tax.name or tax.name,
                    'account_collected_id':tax.account_collected_id.id,
                    'account_paid_id':tax.account_paid_id.id,
                    'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                    'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                    'base_code_id': tax.base_code_id.id,
                    'ref_base_code_id': tax.ref_base_code_id.id,
                    'sequence': tax.sequence,
                    'base_sign': tax.base_sign,
                    'tax_sign': tax.tax_sign,
                    'ref_base_sign': tax.ref_base_sign,
                    'ref_tax_sign': tax.ref_tax_sign,
                    'standard_price': cur_standard_price,
                    'tax_code_id': tax.tax_code_id.id,
                    'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type=='percent':
                amount = cur_standard_price * tax.amount
                data['amount'] = amount
  
            elif tax.type=='fixed':
                data['amount'] = tax.amount
                data['tax_amount']=quantity
#           data['amount'] = quantity
            elif tax.type=='code':
                localdict = {'standard_price':cur_standard_price, 'product':product}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type=='balance':
                data['amount'] = cur_standard_price - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
                data['balance'] = cur_standard_price
  
            amount2 = data.get('amount', 0.0)
            if tax.child_ids:
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = self._unit_compute(cr, uid, tax.child_ids, amount, product, quantity)
                res.extend(child_tax)
                if tax.child_depend:
                    for r in res:
                        for name in ('base','ref_base'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['standard_price'] = latest['standard_price']
                                latest[name+'_code_id'] = False
                        for name in ('tax','ref_tax'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['amount'] = data['amount']
                                latest[name+'_code_id'] = False
            if tax.include_base_amount:
                cur_standard_price+=amount2
        return res
      
    def compute_all(self, cr, uid, taxes, standard_price, quantity, product=None, force_excluded=False):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """
  
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
  
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        

        totalin = totalex = float_round(standard_price * quantity, precision)
        
        quantity = 1
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, standard_price, quantity, product=product)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }
  
  
  
    def _compute(self, cr, uid, taxes, standard_price, quantity, product=None,  precision=None):
        """
        Compute tax values for given PRICE_UNIT, quantity and a buyer/seller ADDRESS_ID.
  
        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
  
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
          

        res = self._unit_compute(cr, uid, taxes, standard_price, product,  quantity)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r.get('balance', 0.0) * quantity, precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0) * quantity, precision)
                total += r['amount']
        return res
      
      
    def _unit_compute_inv(self, cr, uid, taxes, standard_price, product=None):
        taxes = self._applicable(cr, uid, taxes, standard_price,  product)
        res = []
        taxes.reverse()
        cur_standard_price = standard_price
  
        tax_parent_tot = 0.0
        for tax in taxes:
            if (tax.type=='percent') and not tax.include_base_amount:
                tax_parent_tot += tax.amount
  
        for tax in taxes:
            if (tax.type=='fixed') and not tax.include_base_amount:
                cur_standard_price -= tax.amount
  
        for tax in taxes:
            if tax.type=='percent':
                if tax.include_base_amount:
                    amount = cur_standard_price - (cur_standard_price / (1 + tax.amount))
                else:
                    amount = (cur_standard_price / (1 + tax_parent_tot)) * tax.amount
  
            elif tax.type=='fixed':
                amount = tax.amount
  
            elif tax.type=='code':
                localdict = {'standard_price':cur_standard_price, 'product':product}
                exec tax.python_compute_inv in localdict
                amount = localdict['result']
            elif tax.type=='balance':
                amount = cur_standard_price - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
  
            if tax.include_base_amount:
                cur_standard_price -= amount
                todo = 0
            else:
                todo = 1
            res.append({
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_collected_id.id,
                'account_paid_id': tax.account_paid_id.id,
                'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'sequence': tax.sequence,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'standard_price': cur_standard_price,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            })
            if tax.child_ids:
                if tax.child_depend:
                    del res[-1]
                    amount = standard_price
  
            parent_tax = self._unit_compute_inv(cr, uid, tax.child_ids, amount, product)
            res.extend(parent_tax)
  
        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['standard_price'] -= total
            r['todo'] = 0
        return res
      
       
    def compute_inv(self, cr, uid, taxes, standard_price, quantity, product=None, precision=None):

   
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')   
   
        res = self._unit_compute_inv(cr, uid, taxes, standard_price, product)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'] * quantity, precision) - total
            else:
                r['amount'] = round(r['amount'] * quantity, precision)
                total += r['amount']
        return res
       
      
   
account_tax_m15() 



class stock_move(osv.osv):
    _name = 'stock.move'
    _inherit = 'stock.move'    
# 
# 
    def _amount_line_tax(self, cr, uid, move, context=None):
 
        val = 0.0
        for c in self.pool.get('account.tax.m15').compute_all(cr, uid, move.product_id.taxes_id, move.product_id.standard_price, move.product_qty, move.product_id)['taxes']:
            val += c.get('amount', 0.0)
        return val
      
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
 
 
        cur_obj = self.pool.get('res.currency')
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = self.pool.get('res.company').browse(cr, uid, uid).currency_id
 
            val1 += move.product_id.standard_price
            val += self._amount_line_tax(cr, uid, move, context=context)
                  
            res[move.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[move.id]['amount_untaxed'] = val1 - res[move.id]['amount_tax']
            res[move.id]['amount_total'] = res[move.id]['amount_untaxed'] + res[move.id]['amount_tax']
        return res


    def _result_all(self, cr, uid, ids, name, arg, context=None):   
            
        result={}
           
        moves = self.browse(cr, uid, ids)
        for move in moves:
            result[move.id] = move.amount_total * move.product_qty 
         
        return result 
    
    
    _columns = {
           
        'standard_price': fields.related('product_id', 'standard_price', type='float'),
        'taxes_id': fields.related('product_id', 'taxes_id', 'amount', type='float'),
        
        'backorder_id': fields.related('picking_id','backorder_id',type='many2one', relation="m15", string="Back Order of", select=True),
        
        'price_all': fields.function(_result_all, string='Price all', type='float'),
           
        'amount_untaxed': fields.function(_amount_all, type='float', digits_compute=dp.get_precision('Account'), string='Untaxed Amount', multi='sums'),

        'amount_tax': fields.function(_amount_all, type='float', digits_compute=dp.get_precision('Account'), string='Taxes', multi='sums'),
        'amount_total': fields.function(_amount_all, type='float', digits_compute=dp.get_precision('Account'), string='Total', multi='sums'),
        'm15_id': fields.many2one('m15', 'M15', select=True,states={'done': [('readonly', True)]}),


       

                }
     
stock_move()    




