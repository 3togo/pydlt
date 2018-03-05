import torch
from torch.autograd import Variable
from .ganbasetrainer import GANBaseTrainer
from ..util.misc import _get_scalar_value

class FisherGANTrainer(GANBaseTrainer):
    """Fisher GAN trainer. 
    
    Args:
        generator (nn.Module): The generator network.
        discriminator (nn.Module): The discriminator network.
        g_optimizer (torch.optim.Optimizer): Generator Optimizer.
        d_optimizer (torch.optim.Optimizer): Discriminator Optimizer.
        rho (float): Quadratic penalty weight.
        d_iter (int, optional): Number of discriminator steps per generator
            step (default 1).
        add_loss (callable, optional): Extra loss term to be added to GAN
            objective (default None).

    Each iteration returns the mini-batch and a tuple containing:

        - The generator prediction.
        - A dictionary with:
            
            - `ipm_enum`, `ipm_denom`, `ipm_ratio`, `d_loss`, `constraint`,
              `epf`, `eqf`, `epf2`, `eqf2` and `lagrange` if training mode.
            - `g_loss` if validation mode.

    Example:
        >>> trainer = dlt.train.FisherGANTrainer(gen, disc, g_optim, d_optim, rho)
        >>> # Training mode
        >>> trainer.train()
        >>> for batch, (prediction, loss) in trainer(train_data_loader):
        >>>     print(loss['constraint'])
    """
    def __init__(self, generator, discriminator, g_optimizer, d_optimizer, rho, d_iter=1, add_loss=None):
        super(FisherGANTrainer, self).__init__(generator, discriminator, g_optimizer, 
                                                d_optimizer, d_iter, add_loss)
        # Register losses
        self._losses['training'] = ['ipm_enum', 'ipm_denom', 'ipm_ratio', 'd_loss', 'constraint', 
                                    'epf', 'eqf', 'epf2', 'eqf2', 'lagrange']
        self._losses['validation'] = ['g_loss']
        self.rho = rho
        self.alpha = None

    def d_step(self, g_input, real_input):
        for p in self.discriminator.parameters():
            p.requires_grad = True
        self.discriminator.zero_grad()
        if self.alpha is None:
            self.alpha = Variable(g_input.new([0]), requires_grad=True)
        
        if self._use_no_grad:
            with torch.no_grad():
                t_pred = self.generator(Variable(g_input)).data
            prediction = Variable(t_pred)
        else:
            prediction = Variable(self.generator(Variable(g_input, volatile=True)).data)
        vphi_fake = self.discriminator(prediction)
        vphi_real = self.discriminator(Variable(real_input))

        epf, eqf = vphi_real.mean(), vphi_fake.mean()
        epf2, eqf2 = (vphi_real**2).mean(), (vphi_fake**2).mean()
        constraint = (1- (0.5*epf2 + 0.5*eqf2))
        d_loss = -(epf - eqf + self.alpha*constraint - self.rho/2 * constraint**2)
        
        if self.add_loss:
            d_loss = d_loss + self.add_loss(prediction, Variable(real_input))

        d_loss.backward()
        self.d_optimizer.step()
        self.alpha.data += self.rho * self.alpha.grad.data
        self.alpha.grad.data.zero_()

        # IPM
        ipm_enum = _get_scalar_value(epf.data) - _get_scalar_value(eqf.data)
        ipm_denom = (0.5*_get_scalar_value(epf2.data) + 0.5*_get_scalar_value(eqf2.data))**0.5
        ipm_ratio = ipm_enum/ipm_denom
        ret_losses = {'ipm_enum': ipm_enum, 'ipm_denom': ipm_denom, 
                      'ipm_ratio': ipm_ratio, 
                      'd_loss': -_get_scalar_value(d_loss.data), 
                      'constraint': 1 - _get_scalar_value(constraint.data),
                      'epf': _get_scalar_value(epf.data),
                      'eqf': _get_scalar_value(eqf.data),
                      'epf2': _get_scalar_value(epf2.data),
                      'eqf2': _get_scalar_value(eqf2.data),
                      'lagrange': _get_scalar_value(self.alpha.data)}
        self.d_iter_counter += 1
        return prediction.data, ret_losses

    def g_step(self, g_input):
        for p in self.discriminator.parameters():
            p.requires_grad = False
        if self.training:
            self.generator.zero_grad()
            prediction = self.generator(Variable(g_input))
            error = - self.discriminator(prediction).mean()
            error.backward()
            self.g_optimizer.step()
        else:
            if self._use_no_grad:
                with torch.no_grad():
                    prediction = self.generator(Variable(g_input))
                    error = - self.discriminator(prediction).mean()
            else:
                prediction = self.generator(Variable(g_input, volatile=True))
                error = - self.discriminator(prediction).mean()
        return prediction.data, {'g_loss': _get_scalar_value(error.data)}