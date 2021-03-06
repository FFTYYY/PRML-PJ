import torch as tc
from tqdm import tqdm
import pdb
from entry import E
from sklearn.metrics import roc_auc_score , auc , precision_recall_curve 
import random

def evaluate(C , model , dataset , loss_func , epoch_id , run_id , device , eval_name , 
															finger_dict = None , ret_preds = False):
	model = model.eval()
	batch_num = (len(dataset) // C.bs) + int(len(dataset) % C.bs != 0)

	tot_labels = []
	tot_pos_ps = []

	ac_loss = 0
	pbar = tqdm(range(batch_num) , ncols = 130 , desc = "[{0}]{1}ing. Epoch {2}".format(
		run_id , eval_name , epoch_id
	))
	for step , batch_id in enumerate(pbar):

		bdata  = dataset[batch_id * C.bs : (batch_id+1) * C.bs]
		gs 	   = [d[0] for d in bdata]
		smiles = [d[2] for d in bdata]
		labels = [d[1] for d in bdata]
		if finger_dict:
			fingers = [finger_dict.get(s , [0] * C.finger_size) for s in smiles ]
			fingers = tc.LongTensor(fingers).cuda(device) #(bs , 1024)
		else:
			fingers = None

		if -1 in labels: #实际上没有label，也不关心label
			labels = [int(random.random() + 0.5) for _ in labels]

		tot_labels += labels
		labels = tc.LongTensor(labels).cuda(device)

		with tc.no_grad():
			pred  = model(gs , smiles = smiles , fingers = fingers)
			loss = loss_func(pred , labels)
			if not hasattr(model , "softmaxed"):
				pred = tc.softmax(pred , -1)

		ac_loss += float(loss)
		tot_pos_ps += [float(x[1]) for x in pred]

		pbar.set_postfix_str("avg loss = %.4f" % (ac_loss / (step+1)))

	roc_auc = roc_auc_score         (tot_labels , tot_pos_ps)
	p,r,thr = precision_recall_curve(tot_labels , tot_pos_ps)
	prc_auc = auc(r , p)

	E[eval_name + " Loss"  ][str(run_id)].update(ac_loss / batch_num , epoch_id)
	E[eval_name + " ROC-AUC"][str(run_id)].update(roc_auc , epoch_id)
	E[eval_name + " PRC-AUC"][str(run_id)].update(prc_auc , epoch_id)

	if ret_preds:
		return tot_pos_ps
	
	return roc_auc , prc_auc