require(ppcor)
require(boot)

my.pcor.test = function(data, x, y, zvars, method, confint = F, confint.boot.R = 1000) {
  # confint indicates whether or not to report 95% confidence intervals
  # confint.boot.R determines the number of bootstrap replicates
  xvar = enquo(x)
  yvar = enquo(y)
  
  helper = function(data) {
    pcor.test(data %>% select(!! xvar), 
              data %>% select(!! yvar), 
              data %>% select(!!! zvars), 
              method = method)
  }
  
  res = helper(data)
  
  if (confint) {
    res.boot = boot(data = data, statistic = function(data, indices) {
      d = data[indices,]
      helper(d)$estimate
    }, R = confint.boot.R)
    
    res.ci = boot.ci(res.boot, conf = 0.95, type = "norm")
    res$CI.lower = res.ci$normal[2]
    res$CI.upper = res.ci$normal[3]
  }
  
  res
}