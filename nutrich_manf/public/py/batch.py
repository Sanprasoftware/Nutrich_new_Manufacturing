from erpnext.stock.doctype.batch.batch import Batch


class CustomBatch(Batch):
	def before_save(self):
		super().before_save()
		self.manufacturing_date = None
