#import "CustomInput.h"
#import <Lynx/LynxComponentRegistry.h>

@implementation CustomInput

LYNX_LAZY_REGISTER_UI("custom-input")

- (UITextField *)createView {
    UITextField *textField = [[UITextField alloc] init];
    textField.delegate = self;
    textField.borderStyle = UITextBorderStyleNone;
    textField.font = [UIFont systemFontOfSize:14];
    textField.textColor = [UIColor colorWithRed:51/255.0 green:51/255.0 blue:51/255.0 alpha:1.0];
    
    [[NSNotificationCenter defaultCenter] addObserver:self
                                           selector:@selector(textFieldDidChange:)
                                               name:UITextFieldTextDidChangeNotification
                                             object:textField];
    
    return textField;
}

- (void)textFieldDidChange:(NSNotification *)notification {
    [self emitEvent:@"textchange"
             detail:@{
                 @"value": [self.view text] ?: @"",
             }];
}

- (void)emitEvent:(NSString *)name detail:(NSDictionary *)detail {
    LynxCustomEvent *eventInfo = [[LynxDetailEvent alloc] initWithName:name
                                                          targetSign:[self sign]
                                                              detail:detail];
    [self.context.eventEmitter dispatchCustomEvent:eventInfo];
}

@end 